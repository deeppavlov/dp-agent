import asyncio
import itertools
from uuid import uuid4
from typing import Dict, List

from pika import ConnectionParameters
from pika.channel import Channel
from pika.spec import Basic
from pika.spec import BasicProperties

from pika.adapters.select_connection import SelectConnection
from core.transport.base import AbstractTransportGateway
from core.transport.z_dev_config import AGENT_NAME, TRANSPORT_TIMEOUT_SECS, RABBIT_MQ, ANNOTATORS, SKILL_SELECTORS
from core.transport.z_dev_config import SKILLS, RESPONSE_SELECTORS, POSTPROCESSORS


AGENT_IN_EXCHANGE_NAME = f'e_{AGENT_NAME}_in'
AGENT_IN_QUEUE_NAME = f'q_agent_{AGENT_NAME}_in'
AGENT_IN_ROUTING_KEY = '{}.{}'

AGENT_OUT_EXCHANGE_NAME = f'e_{AGENT_NAME}_out'

SERVICE_IN_QUEUE_NAME = 'q_service_{}_in'
SERVICE_IN_ROUTER_KEY_ANY = '{}.any'
SERVICE_IN_ROUTER_KEY_INSTANCE = '{}.instance.{}'


class RabbitMQTransportGatewey(AbstractTransportGateway):
    _loop = asyncio.AbstractEventLoop
    _service_names: List[str]
    _connection_parameters: ConnectionParameters

    _producer_connection: SelectConnection
    _producer_channel: Channel
    _consumer_connection: SelectConnection
    _consumer_channel: Channel

    _processed_tasks: Dict[dict]
    _processed_events: Dict[asyncio.Event]

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._loop = asyncio.get_event_loop()
        self._service_names = [service['name'] for service in itertools.chain[ANNOTATORS, SKILL_SELECTORS, SKILLS,
                                                                                    RESPONSE_SELECTORS, POSTPROCESSORS]]

        self._connection_parameters = ConnectionParameters(host=RABBIT_MQ['host'], port=RABBIT_MQ['PORT'])

    def _connect_producer(self) -> None:
        self._producer_connection = SelectConnection(parameters=self._connection_parameters,
                                                     on_open_callback=self._on_connect_producer)

    def _on_connect_producer(self, connection: SelectConnection) -> None:
        self._producer_channel = connection.channel(on_open_callback=self._on_open_producer_channel)

    def _on_open_producer_channel(self, channel: Channel) -> None:
        channel.exchange_declare(exchange=AGENT_OUT_EXCHANGE_NAME, exchange_type='topic')

        for service_name in self._service_names:
            channel.queue_declare(SERVICE_IN_QUEUE_NAME.format(service_name), durable=True)

    def _connect_consumer(self) -> None:
        self._consumer_connection = SelectConnection(parameters=self._connection_parameters,
                                                     on_open_callback=self._on_connect_consumer)

    def _on_connect_consumer(self, connection: SelectConnection) -> None:
        self._consumer_channel = connection.channel(on_open_callback=self._on_open_consumer_channel)

    def _on_open_consumer_channel(self, channel: Channel) -> None:
        channel.exchange_declare(exchange=AGENT_IN_EXCHANGE_NAME, exchange_type='topic')
        channel.queue_declare(AGENT_IN_QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=AGENT_IN_EXCHANGE_NAME, queue=AGENT_IN_QUEUE_NAME, routing_key='#')
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=AGENT_IN_QUEUE_NAME, on_message_callback=self._on_message_callback)

    def _on_message_callback(self, channel: Channel, method: Basic.Deliver,
                             properties: BasicProperties, body: bytes) -> None:
        pass

    async def process(self, service: str, dialog_state: dict) -> dict:
        pass