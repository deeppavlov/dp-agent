import asyncio
import json
import functools
from abc import abstractmethod
from uuid import uuid4
from typing import Dict, List, Optional, Callable
from logging import getLogger

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, IncomingMessage, Message

from agent_orange.core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase


AGENT_IN_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_e_in'
AGENT_OUT_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_e_out'
AGENT_QUEUE_NAME_TEMPLATE = '{agent_namespace}_q_agent_{agent_name}'
AGENT_ROUTING_KEY_TEMPLATE = '{agent_name}'
SERVICE_QUEUE_NAME_TEMPLATE = '{agent_namespace}_q_service_{service_name}'
SERVICE_ROUTING_KEY_TEMPLATE = '{service_name}.any'
SERVICE_INSTANCE_ROUTING_KEY_TEMPLATE = '{service_name}.instance.{instance_id}'

logger = getLogger(__name__)


# TODO: add proper RabbitMQ authentication
# TODO: add graceful connection close
# TODO: implement sent message timeout (lifetime) control on exchange protocol level
# TODO: add load balancing for stateful skills
class RabbitMQTransportBase:
    _config: dict
    _loop: asyncio.AbstractEventLoop
    _agent_in_exchange: Exchange
    _agent_out_exchange: Exchange
    _connection: Connection
    _agent_in_channel: Channel
    _agent_out_channel: Channel
    _in_queue: Optional[Queue]

    def __init__(self, config: dict, *args, **kwargs):
        super(RabbitMQTransportBase, self).__init__(*args, **kwargs)
        self._config = config
        self._in_queue = None

    async def _connect(self) -> None:
        agent_namespace = self._config['agent_namespace']

        host = self._config['transport']['rabbitmq']['host']
        port = self._config['transport']['rabbitmq']['port']
        logger.info('Starting RabbitMQ connection...')
        self._connection = await aio_pika.connect_robust(loop=self._loop, host=host, port=port)
        logger.info('RabbitMQ connected')

        self._agent_in_channel = await self._connection.channel()
        agent_in_exchange_name = AGENT_IN_EXCHANGE_NAME_TEMPLATE.format(agent_namespace=agent_namespace)
        self._agent_in_exchange = await self._agent_in_channel.declare_exchange(name=agent_in_exchange_name,
                                                                                type=aio_pika.ExchangeType.TOPIC)
        logger.info(f'Declared agent in exchange: {agent_in_exchange_name}')

        self._agent_out_channel = await self._connection.channel()
        agent_out_exchange_name = AGENT_OUT_EXCHANGE_NAME_TEMPLATE.format(agent_namespace=agent_namespace)
        self._agent_out_exchange = await self._agent_in_channel.declare_exchange(name=agent_out_exchange_name,
                                                                                 type=aio_pika.ExchangeType.TOPIC)
        logger.info(f'Declared agent out exchange: {agent_out_exchange_name}')

    @abstractmethod
    async def _setup_queues(self) -> None:
        pass

    @abstractmethod
    async def _on_message_callback(self, message: IncomingMessage) -> None:
        pass


class RabbitMQTransportGateway(RabbitMQTransportBase, TransportGatewayBase):
    _agent_name: str
    _service_responded_events: Dict[str, asyncio.Event]
    _service_responses: Dict[str, dict]

    def __init__(self, config: dict, callback: Callable[[dict], None]) -> None:
        super(RabbitMQTransportGateway, self).__init__(config=config, callback=callback)
        self._loop = asyncio.get_event_loop()
        self._agent_name = self._config['agent']['name']

        self._loop.run_until_complete(self._connect())
        self._loop.run_until_complete(self._setup_queues())
        self._loop.run_until_complete(self._in_queue.consume(callback=self._on_message_callback))
        logger.info('Agent in queue started consuming')

    async def _setup_queues(self) -> None:
        agent_namespace = self._config['agent_namespace']
        in_queue_name = AGENT_QUEUE_NAME_TEMPLATE.format(agent_namespace=agent_namespace, agent_name=self._agent_name)
        self._in_queue = await self._agent_in_channel.declare_queue(name=in_queue_name, durable=True)
        logger.info(f'Declared agent in queue: {in_queue_name}')

        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=self._agent_name)
        await self._in_queue.bind(exchange=self._agent_in_exchange, routing_key=routing_key)
        logger.info(f'Queue: {in_queue_name} bound to routing key: {routing_key}')

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        result: dict = json.loads(message.body, encoding='utf-8')
        task_uuid = result['task_uuid']
        service_name = result['service']
        service_instance_id = result['service_instance_id']
        dialog_state: dict = result['dialog_state']
        logger.debug(f'Received processed task {task_uuid}: service {service_name}, instance: {service_instance_id}, '
                     f'result: {str(dialog_state)}')

        await message.ack()
        await self._loop.create_task(self._callback(dialog_state))

    async def process(self, service: str, dialog_state: dict) -> None:
        task_uuid = str(uuid4())

        task = {
            'agent_name': self._agent_name,
            'task_uuid': task_uuid,
            'dialog_state': dialog_state
        }

        logger.debug(f'Created task {task_uuid}: service {service}, task: {str(dialog_state)}')
        message = Message(body=json.dumps(task).encode('utf-8'), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        routing_key = SERVICE_ROUTING_KEY_TEMPLATE.format(service_name=service)
        await self._agent_out_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Published task {task_uuid} with routing key {routing_key}')


class RabbitMQTransportConnector(RabbitMQTransportBase, TransportConnectorBase):
    _service_caller: ServiceCallerBase
    _service_name: str
    _instance_id: str
    _batch_size: int
    _incoming_messages_buffer: List[IncomingMessage]
    _add_to_buffer_lock: asyncio.Lock
    _infer_lock: asyncio.Lock

    def __init__(self, config: dict, service_caller: ServiceCallerBase) -> None:
        super().__init__(config=config, service_caller=service_caller)
        self._loop = asyncio.get_event_loop()
        self._service_name = self._config['service']['name']
        self._instance_id = self._config['service']['instance_id'] or f'{self._service_name}{str(uuid4())}'
        self._batch_size = self._config['service']['batch_size']

        self._incoming_messages_buffer = []
        self._add_to_buffer_lock = asyncio.Lock()
        self._infer_lock = asyncio.Lock()

        self._loop.run_until_complete(self._connect())
        self._loop.run_until_complete(self._setup_queues())
        self._loop.run_until_complete(self._in_queue.consume(callback=self._on_message_callback))
        logger.info(f'Service in queue started consuming')

        self._loop.run_forever()

    async def _setup_queues(self) -> None:
        agent_namespace = self._config['agent_namespace']

        in_queue_name = SERVICE_QUEUE_NAME_TEMPLATE.format(agent_namespace=agent_namespace,
                                                           service_name=self._service_name)

        self._in_queue = await self._agent_out_channel.declare_queue(name=in_queue_name, durable=True)
        logger.info(f'Declared service in queue: {in_queue_name}')

        any_instance_routing_key = SERVICE_ROUTING_KEY_TEMPLATE.format(service_name=self._service_name)
        await self._in_queue.bind(exchange=self._agent_out_exchange, routing_key=any_instance_routing_key)
        logger.info(f'Queue: {in_queue_name} bound to routing key: {any_instance_routing_key}')

        this_instance_routing_key = SERVICE_INSTANCE_ROUTING_KEY_TEMPLATE.format(service_name=self._service_name,
                                                                                 instance_id=self._instance_id)

        await self._in_queue.bind(exchange=self._agent_out_exchange, routing_key=this_instance_routing_key)
        logger.info(f'Queue: {in_queue_name} bound to routing key: {this_instance_routing_key}')

        await self._agent_out_channel.set_qos(prefetch_count=self._batch_size * 2)

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        await self._add_to_buffer_lock.acquire()
        self._incoming_messages_buffer.append(message)
        logger.debug('Incoming message received')

        if len(self._incoming_messages_buffer) < self._batch_size:
            self._add_to_buffer_lock.release()

        await self._infer_lock.acquire()
        try:
            messages_batch = self._incoming_messages_buffer

            if messages_batch:
                self._incoming_messages_buffer = []

                if self._add_to_buffer_lock.locked():
                    self._add_to_buffer_lock.release()

                tasks_batch = [json.loads(message.body, encoding='utf-8') for message in messages_batch]
                await self._process_tasks(tasks_batch)

                for message in messages_batch:
                    await message.ack()

            elif self._add_to_buffer_lock.locked():
                self._add_to_buffer_lock.release()
        finally:
            self._infer_lock.release()

    async def _process_tasks(self, tasks_batch: List[dict]) -> None:
        task_agent_names_batch, task_uuids_batch, dialog_states_batch = \
            zip(*[(task['agent_name'], task['task_uuid'], task['dialog_state']) for task in tasks_batch])

        logger.debug(f'Prepared for infering tasks {str(task_uuids_batch)}')

        try:
            inferer = functools.partial(self._infer, dialog_states_batch)
            infer_timeout = self._config['service']['infer_timeout_sec']
            responses_batch = await asyncio.wait_for(self._loop.run_in_executor(executor=None, func=inferer),
                                                     infer_timeout)
            logger.debug(f'Processed tasks {str(task_uuids_batch)}')
        except asyncio.TimeoutError:
            responses_batch = None

        # TODO: make correct empty responses handling
        if responses_batch:
            await asyncio.wait([self._send_results(task_agent_names_batch[i], task_uuids_batch[i], dialog_state)
                                for i, dialog_state in enumerate(responses_batch)])

    async def _send_results(self, agent_name: str, task_uuid: str, dialog_state: dict) -> None:
        result = {
            'service': self._service_name,
            'service_instance_id': self._instance_id,
            'task_uuid': task_uuid,
            'dialog_state': dialog_state
        }

        message = Message(body=json.dumps(result).encode('utf-8'), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=agent_name)
        await self._agent_in_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Sent response for task {str(task_uuid)} with routing key {routing_key}')
