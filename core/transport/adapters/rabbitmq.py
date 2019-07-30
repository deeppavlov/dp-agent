import asyncio
import itertools
import json
import functools
from uuid import uuid4
from typing import Dict, List, Optional

import aio_pika
from aio_pika import Connection, Channel, Exchange, IncomingMessage, Message

from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase
from core.transport.z_dev_config import AGENT_NAME, TRANSPORT_TIMEOUT_SECS, RABBIT_MQ, ANNOTATORS, SKILL_SELECTORS
from core.transport.z_dev_config import SKILLS, RESPONSE_SELECTORS, POSTPROCESSORS, SERVICE_CONFIG


AGENT_IN_EXCHANGE_NAME = f'e_{AGENT_NAME}_in'
AGENT_IN_QUEUE_NAME = f'q_agent_{AGENT_NAME}_in'
AGENT_OUT_EXCHANGE_NAME = f'e_{AGENT_NAME}_out'
SERVICE_IN_QUEUE_NAME = 'q_service_{}_in'
SERVICE_IN_ROUTING_KEY_ANY = '{}.anyinstance'
SERVICE_IN_ROUTING_KEY_INSTANCE = '{}.instance.{}'


# TODO: add graceful connection close
# TODO: add load balancing for stateful skills
# TODO: implement sent message timeout control
# TODO: think about agent incoming messages acknowledge removal
# TODO: decide, if loop __init__ argument needed
class RabbitMQTransportGateway(TransportGatewayBase):
    _loop: asyncio.AbstractEventLoop
    _service_names: List[str]
    _connection: Connection
    _channel: Channel
    _out_exchange: Exchange
    _in_exchange: Exchange
    _service_responded_events: Dict[str, asyncio.Event]
    _service_responses: Dict[str, dict]

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._service_names = [service['name'] for service in itertools.chain[ANNOTATORS, SKILL_SELECTORS, SKILLS,
                                                                              RESPONSE_SELECTORS, POSTPROCESSORS]]

        self._service_responded_events = {}
        self._service_responses = {}
        self._loop.create_task(self._connect())

    # TODO: add proper RabbitMQ authentication
    async def _connect(self) -> None:
        self._connection = await aio_pika.connect(loop=self._loop, host=RABBIT_MQ['host'], port=RABBIT_MQ['port'])
        self._channel = await self._connection.channel()

        # declare producer exchange and out queues
        self._out_exchange = await self._channel.declare_exchange(name=AGENT_OUT_EXCHANGE_NAME,
                                                                  type=aio_pika.ExchangeType.TOPIC)

        for service_name in self._service_names:
            queue = await self._channel.declare_queue(name=SERVICE_IN_QUEUE_NAME.format(service_name), durable=True)
            await queue.bind(exchange=self._out_exchange, routing_key=SERVICE_IN_ROUTING_KEY_ANY.format(service_name))

        # declare consumer exchange and in queue
        self._in_exchange = await self._channel.declare_exchange(name=AGENT_IN_EXCHANGE_NAME,
                                                                 type=aio_pika.ExchangeType.TOPIC)

        queue = await self._channel.declare_queue(name=AGENT_IN_QUEUE_NAME, durable=True)
        await queue.bind(exchange=self._in_exchange, routing_key='#')
        await queue.consume(callback=self._on_message_callback)

    async def _on_message_callback(self, message: IncomingMessage):
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
            'task_uuid': task_uuid,
            'dialog_state': dialog_state
        }

        self._service_responded_events[task_uuid] = asyncio.Event()
        message = Message(body=json.dumps(task), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await self._out_exchange.publish(message=message, routing_key=SERVICE_IN_ROUTING_KEY_ANY.format(service))

        try:
            await asyncio.wait_for(self._service_responded_events[task_uuid].wait(), TRANSPORT_TIMEOUT_SECS)
            updated_dialog_state = self._service_responses.pop(task_uuid, None)
        except asyncio.TimeoutError:
            updated_dialog_state = None
        finally:
            self._service_responded_events.pop(task_uuid, None)

        return updated_dialog_state


# TODO: add graceful connection close
# TODO: add load balancing for stateful skills
# TODO: decide, if loop __init__ argument needed
class RabbitMQTransportConnector(TransportConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _service_caller: ServiceCallerBase
    _service_name: str
    _instance_id: str
    _service_router_key_any: str
    _service_router_key_instance: str
    _batch_size: int
    _infer_timeout: float
    _connection: Connection
    _channel: Channel
    _out_exchange: Exchange
    _in_exchange: Exchange
    _incoming_messages_buffer: List[IncomingMessage]
    _add_to_buffer_lock: asyncio.Lock
    _infer_lock: asyncio.Lock

    def __init__(self, loop: asyncio.AbstractEventLoop, service_caller: ServiceCallerBase) -> None:
        super().__init__(service_caller=service_caller)
        self._loop = loop

        self._service_name = SERVICE_CONFIG['name']
        self._instance_id = SERVICE_CONFIG['instance_id'] or f'{self._service_name}{str(uuid4())}'
        self._service_router_key_any.format(self._service_name)
        self._service_router_key_instance.format(self._service_name, self._instance_id)
        self._batch_size = SERVICE_CONFIG['batch_size']
        self._infer_timeout = TRANSPORT_TIMEOUT_SECS

        self._incoming_messages_buffer = []

        self._add_to_buffer_lock = asyncio.Lock()
        self._infer_lock = asyncio.Lock()

        self._loop.create_task(self._connect())

    # TODO: add proper RabbitMQ authentication
    async def _connect(self) -> None:
        self._connection = await aio_pika.connect(loop=self._loop, host=RABBIT_MQ['host'], port=RABBIT_MQ['port'])
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._batch_size)

        # declare producer exchange and out queues
        self._out_exchange = await self._channel.declare_exchange(name=AGENT_IN_EXCHANGE_NAME,
                                                                  type=aio_pika.ExchangeType.TOPIC)

        await self._channel.declare_queue(name=AGENT_IN_QUEUE_NAME, durable=True)

        # declare consumer exchange and in queue
        self._in_exchange = await self._channel.declare_exchange(name=AGENT_OUT_EXCHANGE_NAME,
                                                                 type=aio_pika.ExchangeType.TOPIC)

        queue_name = SERVICE_IN_QUEUE_NAME.format(self._service_name)
        queue = await self._channel.declare_queue(name=queue_name, durable=True)

        await queue.bind(exchange=self._in_exchange, routing_key=self._service_router_key_any)
        await queue.consume(callback=self._on_message_callback)

    async def _on_message_callback(self, message: IncomingMessage) -> None:
        await self._add_to_buffer_lock.acquire()
        self._incoming_messages_buffer.append(message)

        if len(self._incoming_messages_buffer) < self._batch_size:
            self._add_to_buffer_lock.release()

        with self._infer_lock:
            messages_batch = self._incoming_messages_buffer

            if messages_batch:
                self._incoming_messages_buffer = []
                tasks_batch = [json.loads(message.body, encoding='utf-8') for message in messages_batch]

                for message in messages_batch:
                    await message.ack()

                await self._process_tasks(tasks_batch)

    async def _process_tasks(self, tasks_batch: List[dict]) -> None:
        task_uuids_batch, dialog_states_batch = \
            zip(*[(task['task_uuid'], task['dialog_state']) for task in tasks_batch])

        try:
            inferer = functools.partial(self._infer, task_uuids_batch)
            responses_batch = await asyncio.wait_for(self._loop.run_in_executor(executor=None, func=inferer),
                                                     self._infer_timeout)
        except asyncio.TimeoutError:
            responses_batch = None

        if responses_batch:
            for i, dialog_state in enumerate(responses_batch):
                await self._loop.create_task(self._send_results(task_uuids_batch[i], dialog_state))

    async def _send_results(self, task_uuid: str, dialog_state: dict) -> None:
        pass
