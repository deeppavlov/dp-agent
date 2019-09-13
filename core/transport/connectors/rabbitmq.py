import asyncio
import json
import functools
import time
from abc import abstractmethod
from uuid import uuid4
from typing import Dict, List, Optional, Callable, Awaitable
from logging import getLogger

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, IncomingMessage, Message

from core.transport.base import AgentGatewayBase, ServiceGatewayBase, ChannelGatewayBase
from core.transport.base import TServiceCaller
from core.transport.messages import ServiceTaskMessage, ServiceResponseMessage, ToChannelMessage, FromChannelMessage
from core.transport.messages import TMessageBase, get_transport_message


AGENT_IN_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_e_in'
AGENT_OUT_EXCHANGE_NAME_TEMPLATE = '{agent_namespace}_e_out'
AGENT_QUEUE_NAME_TEMPLATE = '{agent_namespace}_q_agent_{agent_name}'
AGENT_ROUTING_KEY_TEMPLATE = 'agent.{agent_name}'

SERVICE_QUEUE_NAME_TEMPLATE = '{agent_namespace}_q_service_{service_name}'
SERVICE_ROUTING_KEY_TEMPLATE = 'service.{service_name}.any'
SERVICE_INSTANCE_ROUTING_KEY_TEMPLATE = 'service.{service_name}.instance.{instance_id}'

CHANNEL_QUEUE_NAME_TEMPLATE = '{agent_namespace}_{agent_name}_q_channel_{channel_id}'
CHANNEL_ROUTING_KEY_TEMPLATE = 'agent.{agent_name}.channel.{channel_id}.any'

logger = getLogger(__name__)


# TODO: add handling of: Server connection probably hang, last heartbeat received 1067.857 seconds ago
# TODO: add proper RabbitMQ SSL authentication
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
    _response_timeout_sec: int

    def __init__(self, config: dict, *args, **kwargs):
        super(RabbitMQTransportBase, self).__init__(*args, **kwargs)
        self._config = config
        self._in_queue = None
        self._response_timeout_sec = config['agent']['response_timeout_sec']

    async def _connect(self) -> None:
        agent_namespace = self._config['agent_namespace']

        host = self._config['transport']['rabbitmq']['host']
        port = self._config['transport']['rabbitmq']['port']
        login = self._config['transport']['rabbitmq']['login']
        password = self._config['transport']['rabbitmq']['password']
        virtualhost = self._config['transport']['rabbitmq']['virtualhost']

        logger.info('Starting RabbitMQ connection...')

        while True:
            try:
                self._connection = await aio_pika.connect_robust(loop=self._loop, host=host, port=port, login=login,
                                                                 password=password, virtualhost=virtualhost)

                logger.info('RabbitMQ connected')
                break
            except ConnectionError:
                reconnect_timeout = 5
                logger.error(f'RabbitMQ connection error, making another attempt in {reconnect_timeout} secs')
                time.sleep(reconnect_timeout)

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


class RabbitMQAgentGateway(RabbitMQTransportBase, AgentGatewayBase):
    _agent_name: str
    _service_responded_events: Dict[str, asyncio.Event]
    _service_responses: Dict[str, dict]

    def __init__(self, config: dict,
                 on_service_callback: Callable[[Dict], Awaitable],
                 on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:

        super(RabbitMQAgentGateway, self).__init__(config=config,
                                                   on_service_callback=on_service_callback,
                                                   on_channel_callback=on_channel_callback)

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
        message_in: TMessageBase = get_transport_message(json.loads(message.body, encoding='utf-8'))
        await message.ack()

        if isinstance(message_in, ServiceResponseMessage):
            logger.debug(f'Received service response message with task uuid {message_in.task_uuid}')
            partial_dialog_state = message_in.partial_dialog_state
            await self._loop.create_task(self._on_service_callback(partial_dialog_state=partial_dialog_state))

        elif isinstance(message_in, FromChannelMessage):
            utterance = message_in.utterance
            channel_id = message_in.channel_id
            user_id = message_in.user_id
            reset_dialog = message_in.reset_dialog
            logger.debug(f'Received message from channel {channel_id}, user {user_id}')
            await self._loop.create_task(self._on_channel_callback(utterance=utterance,
                                                                   channel_id=channel_id,
                                                                   user_id=user_id,
                                                                   reset_dialog=reset_dialog))

    async def send_to_service(self, service_name: str, dialog_state: dict) -> None:
        task_uuid = str(uuid4())
        task = ServiceTaskMessage(agent_name=self._agent_name, task_uuid=task_uuid, dialog_state=dialog_state)
        logger.debug(f'Created task {task_uuid} to service {service_name} with dialog state: {str(dialog_state)}')

        message = Message(body=json.dumps(task.to_json()).encode('utf-8'),
                          delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                          expiration=self._response_timeout_sec)

        routing_key = SERVICE_ROUTING_KEY_TEMPLATE.format(service_name=service_name)
        await self._agent_out_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Published task {task_uuid} with routing key {routing_key}')

    async def send_to_channel(self, channel_id: str, user_id: str, response: str) -> None:
        channel_message = ToChannelMessage(agent_name=self._agent_name,
                                           channel_id=channel_id,
                                           user_id=user_id,
                                           response=response)

        channel_message_json = channel_message.to_json()
        message = Message(body=json.dumps(channel_message_json).encode('utf-8'),
                          delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                          expiration=self._response_timeout_sec)

        routing_key = CHANNEL_ROUTING_KEY_TEMPLATE.format(agent_name=self._agent_name, channel_id=channel_id)
        await self._agent_out_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Published channel message: {str(channel_message_json)}')


class RabbitMQServiceGateway(RabbitMQTransportBase, ServiceGatewayBase):
    _service_caller: TServiceCaller
    _service_name: str
    _instance_id: str
    _batch_size: int
    _incoming_messages_buffer: List[IncomingMessage]
    _add_to_buffer_lock: asyncio.Lock
    _infer_lock: asyncio.Lock

    def __init__(self, config: dict, service_caller: TServiceCaller) -> None:
        super(RabbitMQServiceGateway, self).__init__(config=config, service_caller=service_caller)
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

                tasks_batch = [ServiceTaskMessage.from_json(json.loads(message.body, encoding='utf-8'))
                               for message in messages_batch]

                processed_ok = await self._process_tasks(tasks_batch)

                if processed_ok:
                    for message in messages_batch:
                        await message.ack()
                else:
                    for message in messages_batch:
                        await message.reject()

            elif self._add_to_buffer_lock.locked():
                self._add_to_buffer_lock.release()
        finally:
            self._infer_lock.release()

    async def _process_tasks(self, tasks_batch: List[ServiceTaskMessage]) -> bool:
        task_agent_names_batch, task_uuids_batch, dialog_states_batch = \
            zip(*[(task.agent_name, task.task_uuid, task.dialog_state) for task in tasks_batch])

        logger.debug(f'Prepared for infering tasks {str(task_uuids_batch)}')

        # TODO: Think about proper infer errors and aknowledge handling
        try:
            inferer = functools.partial(self._infer, dialog_states_batch)
            infer_timeout = self._config['service']['infer_timeout_sec']
            responses_batch = await asyncio.wait_for(self._loop.run_in_executor(executor=None, func=inferer),
                                                     infer_timeout)
            logger.debug(f'Processed tasks {str(task_uuids_batch)}')
        except asyncio.TimeoutError:
            responses_batch = None

        if responses_batch:
            await asyncio.wait([self._send_results(task_agent_names_batch[i], task_uuids_batch[i], partial_state)
                                for i, partial_state in enumerate(responses_batch)])
            return True
        else:
            return False

    async def _send_results(self, agent_name: str, task_uuid: str, partial_dialog_state: dict) -> None:
        result = ServiceResponseMessage(agent_name=agent_name,
                                        task_uuid=task_uuid,
                                        service_name=self._service_name,
                                        service_instance_id=self._instance_id,
                                        partial_dialog_state=partial_dialog_state)

        message = Message(body=json.dumps(result.to_json()).encode('utf-8'),
                          delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                          expiration=self._response_timeout_sec)

        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=agent_name)
        await self._agent_in_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Sent response for task {str(task_uuid)} with routing key {routing_key}')


class RabbitMQChannelGateway(RabbitMQTransportBase, ChannelGatewayBase):
    _agent_name: str
    _channel_id: str

    def __init__(self, config: dict, to_channel_callback: Callable[[str, str], Awaitable]) -> None:
        super(RabbitMQChannelGateway, self).__init__(config=config, to_channel_callback=to_channel_callback)
        self._loop = asyncio.get_event_loop()
        self._agent_name = self._config['agent']['name']
        self._channel_id = self._config['channel']['id']

        self._loop.run_until_complete(self._connect())
        self._loop.run_until_complete(self._setup_queues())
        self._loop.run_until_complete(self._in_queue.consume(callback=self._on_message_callback))
        logger.info(f'Channel connector messages queue from agent started consuming')

    async def _setup_queues(self) -> None:
        agent_namespace = self._config['agent_namespace']

        in_queue_name = CHANNEL_QUEUE_NAME_TEMPLATE.format(agent_namespace=agent_namespace,
                                                           agent_name=self._agent_name,
                                                           channel_id=self._channel_id)

        self._in_queue = await self._agent_out_channel.declare_queue(name=in_queue_name, durable=True)
        logger.info(f'Declared channel in queue: {in_queue_name}')

        routing_key = CHANNEL_ROUTING_KEY_TEMPLATE.format(agent_name=self._agent_name, channel_id=self._channel_id)
        await self._in_queue.bind(exchange=self._agent_out_exchange, routing_key=routing_key)
        logger.info(f'Queue: {in_queue_name} bound to routing key: {routing_key}')

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        message_json = json.loads(message.body, encoding='utf-8')
        message_to_channel: ToChannelMessage = ToChannelMessage.from_json(message_json)
        await self._loop.create_task(self._to_channel_callback(message_to_channel.user_id, message_to_channel.response))
        await message.ack()
        logger.debug(f'Processed message to channel: {str(message_json)}')

    async def send_to_agent(self, utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        message_from_channel = FromChannelMessage(agent_name=self._agent_name,
                                                  channel_id=channel_id,
                                                  user_id=user_id,
                                                  utterance=utterance,
                                                  reset_dialog=reset_dialog)

        message_json = message_from_channel.to_json()
        message = Message(body=json.dumps(message_json).encode('utf-8'),
                          delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                          expiration=self._response_timeout_sec)

        routing_key = AGENT_ROUTING_KEY_TEMPLATE.format(agent_name=self._agent_name)
        await self._agent_in_exchange.publish(message=message, routing_key=routing_key)
        logger.debug(f'Processed message to agent: {str(message_json)}')
