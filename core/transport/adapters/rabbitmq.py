import asyncio
import itertools
import json
from uuid import uuid4
from typing import Dict, List, Optional

import aio_pika
from aio_pika import Connection, Channel, Exchange, IncomingMessage, Message

from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase
from core.transport.z_dev_config import AGENT_NAME, TRANSPORT_TIMEOUT_SECS, RABBIT_MQ, ANNOTATORS, SKILL_SELECTORS
from core.transport.z_dev_config import SKILLS, RESPONSE_SELECTORS, POSTPROCESSORS, SERVICE_CONFIG


AGENT_IN_EXCHANGE_NAME = f'e_{AGENT_NAME}_in'
AGENT_IN_QUEUE_NAME = f'q_agent_{AGENT_NAME}_in'
AGENT_IN_ROUTING_KEY = '{}.{}'

AGENT_OUT_EXCHANGE_NAME = f'e_{AGENT_NAME}_out'

SERVICE_IN_QUEUE_NAME = 'q_service_{}_in'
SERVICE_IN_ROUTING_KEY_ANY = '{}.anyinstance'
SERVICE_IN_ROUTING_KEY_INSTANCE = '{}.instance.{}'


# TODO: add graceful connection close
# TODO: add load balancing for stateful skills
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
            queue = await self._channel.declare_queue(name=service_name, durable=True)
            await queue.bind(exchange=self._out_exchange, routing_key=SERVICE_IN_ROUTING_KEY_ANY.format(service_name))

        # declare consumer exchange and in queue
        self._in_exchange = await self._channel.declare_exchange(name=AGENT_IN_EXCHANGE_NAME,
                                                                 type=aio_pika.ExchangeType.TOPIC)

        queue = await self._channel.declare_queue(name=AGENT_IN_QUEUE_NAME, durable=True)
        await queue.bind(exchange=self._in_exchange, routing_key='#')
        await queue.consume(callback=self._on_message_callback)

    async def _on_message_callback(self, message: IncomingMessage):
        processed_message: dict = json.loads(message.body, encoding='utf-8')
        message_uuid = processed_message['message_uuid']
        dialog_state = processed_message['dialog_state']
        message_event = self._service_responded_events.pop(message_uuid, None)

        if message_event and not message_event.is_set():
            self._service_responses[message_uuid] = dialog_state
            message_event.set()

        await message.ack()

    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        message_uuid = str(uuid4())
        message_body = {
            'message_uuid': message_uuid,
            'dialog_state': dialog_state
        }

        self._service_responded_events[message_uuid] = asyncio.Event()
        message = Message(body=json.dumps(message_body), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await self._out_exchange.publish(message=message, routing_key=SERVICE_IN_ROUTING_KEY_ANY.format(service))

        try:
            await asyncio.wait_for(self._service_responded_events[message_uuid].wait(), TRANSPORT_TIMEOUT_SECS)
            updated_dialog_state = self._service_responses.pop(message_uuid, None)
        except asyncio.TimeoutError:
            updated_dialog_state = None
        finally:
            self._service_responded_events.pop(message_uuid, None)

        return updated_dialog_state


class RabbitMQTransportConnector(TransportConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _service_name: str
    _instance_id: str
    _service_caller: ServiceCallerBase
    _connection: Channel
    _channel: Channel
    _out_exchange: Exchange
    _in_exchange: Exchange

    def __init__(self, service_caller: ServiceCallerBase) -> None:
        super().__init__(service_caller=service_caller)

        self._loop = asyncio.get_event_loop()
        self._connection_parameters = ConnectionParameters(host=RABBIT_MQ['host'], port=RABBIT_MQ['PORT'])

    def _connect(self) -> None:
        self._connection = SelectConnection(parameters=self._connection_parameters, on_open_callback=self._on_connect)

    def _on_connect(self, connection: SelectConnection) -> None:
        self._channel = connection.channel(on_open_callback=self._on_open_channel)

    def _on_open_channel(self, channel: Channel) -> None:
        # declare producer exchange and out queue
        channel.exchange_declare(exchange=AGENT_IN_EXCHANGE_NAME, exchange_type='topic')
        channel.queue_declare(AGENT_IN_QUEUE_NAME, durable=True)

        # declare consumer exchange and in queue
        channel.exchange_declare(exchange=AGENT_OUT_EXCHANGE_NAME, exchange_type='topic')

        queue_name = SERVICE_IN_QUEUE_NAME.format()
        channel.queue_declare(queue_name, durable=True)

        any_instance_router_key = SERVICE_IN_ROUTING_KEY_ANY.format(self._service_name)
        channel.queue_bind(exchange=AGENT_OUT_EXCHANGE_NAME, queue=queue_name, routing_key=any_instance_router_key)

        channel.basic_qos(prefetch_count=SERVICE_CONFIG['batch_size'])
        channel.basic_consume(queue=AGENT_IN_QUEUE_NAME, on_message_callback=self._on_message_callback)

    # TODO: implement _on_message_callback

    async def _on_message_callback_1(self, channel: Channel, method: Basic.Deliver,
                                   _properties: BasicProperties, body: bytes) -> None:
        processed_message: dict = json.loads(body, encoding='utf-8')
        message_uuid = processed_message['message_uuid']
        dialog_state = processed_message['dialog_state']
        message_event = self._service_responded_events.pop(message_uuid, None)

        if message_event and not message_event.is_set():
            self._service_responses[message_uuid] = dialog_state
            message_event.set()

        # TODO: think if message acknowledge really needed here
        channel.basic_ack(delivery_tag=method.delivery_tag)

    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        message_uuid = str(uuid4())

        message = {
            'message_uuid': message_uuid,
            'dialog_state': dialog_state
        }

        self._service_responded_events[message_uuid] = asyncio.Event()
        self._channel.basic_publish(exchange=AGENT_OUT_EXCHANGE_NAME,
                                    routing_key=SERVICE_IN_ROUTING_KEY_ANY.format(service),
                                    body=json.dumps(message),
                                    properties=pika.BasicProperties(delivery_mode=2))

        try:
            await asyncio.wait_for(self._service_responded_events[message_uuid].wait(), TRANSPORT_TIMEOUT_SECS)
            updated_dialog_state = self._service_responses.pop(message_uuid, None)
        except asyncio.TimeoutError:
            updated_dialog_state = None
        finally:
            self._service_responded_events.pop(message_uuid, None)

        return updated_dialog_state