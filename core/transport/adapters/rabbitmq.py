import asyncio
import json
import functools
from abc import ABCMeta, abstractmethod
from uuid import uuid4
from typing import Dict, List, Optional

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, IncomingMessage, Message

from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase


AGENT_IN_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_in'
AGENT_OUT_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_out'
AGENT_QUEUE_NAME_TEMPLATE = '{agent_namespace}_{agent_name}'
AGENT_ROUTING_KEY_TEMPLATE = '{agent_name}'
SERVICE_QUEUE_NAME_TEMPLATE = '{agent_namespace}_{service_name}'
SERVICE_ROUTING_KEY_TEMPLATE = '{service_name}.any'
SERVICE_INSTANCE_ROUTING_KEY_TEMPLATE = '{service_name}.instance.{instance_id}'


# TODO: add proper RabbitMQ authentication
# TODO: add graceful connection close
# TODO: implement sent message timeout (lifetime) control on exchange protocol level
# TODO: add load balancing for stateful skills
class RabbitMQTransportBase(metaclass=ABCMeta):
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
        self._loop = asyncio.get_event_loop()
        self._loop.run_until_complete(self._connect())

    async def _connect(self) -> None:
        agent_namespace = self._config['agent_namespace']

        host = self._config['transport']['rabbitmq']['host']
        port = self._config['transport']['rabbitmq']['port']
        self._connection = await aio_pika.connect(loop=self._loop, host=host, port=port)

        self._agent_in_channel = await self._connection.channel()
        agent_in_exchange_name = AGENT_IN_EXCHANGE_NAME_TEMPLATE.format(agent_namespace=agent_namespace)
        self._agent_in_exchange = await self._agent_in_channel.declare_exchange(name=agent_in_exchange_name,
                                                                                type=aio_pika.ExchangeType.TOPIC)

        self._agent_out_channel = await self._connection.channel()
        agent_out_exchange_name = AGENT_OUT_EXCHANGE_NAME_TEMPLATE.format(agent_namespace=agent_namespace)
        self._agent_out_exchange = await self._agent_in_channel.declare_exchange(name=agent_out_exchange_name,
                                                                                 type=aio_pika.ExchangeType.TOPIC)

        await self._setup_queues()

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

    def __init__(self, config: dict) -> None:
        super(RabbitMQTransportGateway, self).__init__(config)

        self._agent_name = self._config['agent']['name']
        self._service_responded_events = {}
        self._service_responses = {}

    async def _setup_queues(self) -> None:
        agent_namespace = self._config['agent_namespace']
        in_queue_name = AGENT_QUEUE_NAME_TEMPLATE.format(agent_namespace=agent_namespace, agent_name=self._agent_name)
        self._in_queue = await self._agent_in_channel.declare_queue(name=in_queue_name, durable=True)

        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=self._agent_name)
        await self._in_queue.bind(exchange=self._agent_in_exchange, routing_key=routing_key)
        await self._in_queue.consume(callback=self._on_message_callback)

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        result: dict = json.loads(message.body, encoding='utf-8')
        message_uuid = result['message_uuid']
        dialog_state = result['dialog_state']
        message_event = self._service_responded_events.pop(message_uuid, None)

        if message_event and not message_event.is_set():
            self._service_responses[message_uuid] = dialog_state
            message_event.set()

        await message.ack()

    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        task_uuid = str(uuid4())

        task = {
            'agent_name': self._agent_name,
            'task_uuid': task_uuid,
            'dialog_state': dialog_state
        }

        self._service_responded_events[task_uuid] = asyncio.Event()
        message = Message(body=json.dumps(task), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        routing_key = SERVICE_ROUTING_KEY_TEMPLATE.format(service)
        await self._agent_out_exchange.publish(message=message, routing_key=routing_key)

        try:
            await asyncio.wait_for(self._service_responded_events[task_uuid].wait(),
                                   self._config['transport']['timeout_sec'])

            updated_dialog_state = self._service_responses.pop(task_uuid, None)
        except asyncio.TimeoutError:
            updated_dialog_state = None
        finally:
            self._service_responded_events.pop(task_uuid, None)

        return updated_dialog_state


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

        self._service_name = self._config['service']['service_name']
        self._instance_id = self._config['service']['instance_id'] or f'{self._service_name}{str(uuid4())}'
        self._batch_size = self._config['service']['batch_size']

        self._incoming_messages_buffer = []
        self._add_to_buffer_lock = asyncio.Lock()
        self._infer_lock = asyncio.Lock()

    async def _setup_queues(self) -> None:
        agent_namespace = self._config['agent_namespace']

        in_queue_name = SERVICE_QUEUE_NAME_TEMPLATE.format(agent_namespace=agent_namespace,
                                                           service_name=self._service_name)

        self._in_queue = await self._agent_out_channel.declare_queue(name=in_queue_name, durable=True)

        any_instance_routing_key = SERVICE_ROUTING_KEY_TEMPLATE.format(service_name=self._service_name)
        await self._in_queue.bind(exchange=self._agent_out_exchange, routing_key=any_instance_routing_key)

        this_instance_routing_key = SERVICE_INSTANCE_ROUTING_KEY_TEMPLATE.format(service_name=self._service_name,
                                                                                 instance_id=self._instance_id)

        await self._in_queue.bind(exchange=self._agent_out_exchange, routing_key=this_instance_routing_key)

        await self._agent_out_channel.set_qos(prefetch_count=self._batch_size)
        await self._in_queue.consume(callback=self._on_message_callback)

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        await self._add_to_buffer_lock.acquire()
        self._incoming_messages_buffer.append(message)

        if len(self._incoming_messages_buffer) < self._batch_size:
            self._add_to_buffer_lock.release()

        with self._infer_lock:
            messages_batch = self._incoming_messages_buffer

            if messages_batch:
                self._incoming_messages_buffer = []

                if self._add_to_buffer_lock.locked():
                    self._add_to_buffer_lock.release()

                for message in messages_batch:
                    await message.ack()

                tasks_batch = [json.loads(message.body, encoding='utf-8') for message in messages_batch]
                await self._process_tasks(tasks_batch)

            elif self._add_to_buffer_lock.locked():
                self._add_to_buffer_lock.release()

    async def _process_tasks(self, tasks_batch: List[dict]) -> None:
        task_agent_names_batch, task_uuids_batch, dialog_states_batch = \
            zip(*[(task['agent_name'], task['task_uuid'], task['dialog_state']) for task in tasks_batch])

        try:
            inferer = functools.partial(self._infer, task_uuids_batch)
            infer_timeout = self._config['transport']['timeout_sec']
            responses_batch = await asyncio.wait_for(self._loop.run_in_executor(executor=None, func=inferer),
                                                     infer_timeout)
        except asyncio.TimeoutError:
            responses_batch = None

        if responses_batch:
            await asyncio.wait([self._send_results(task_agent_names_batch[i], task_uuids_batch[i], dialog_state)
                                for i, dialog_state in enumerate(responses_batch)])

    async def _send_results(self, agent_name: str, task_uuid: str, dialog_state: dict) -> None:
        result = {
            'service_instance_id': self._instance_id,
            'task_uuid': task_uuid,
            'dialog_state': dialog_state
        }

        message = Message(body=json.dumps(result), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=agent_name)
        await self._agent_in_exchange.publish(message=message, routing_key=routing_key)
