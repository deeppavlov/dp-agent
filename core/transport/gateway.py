import asyncio
import itertools
from typing import Dict, List

from pika.channel import Channel
from pika.adapters.select_connection import SelectConnection

from core.transport.dev_transport_config import ANNOTATORS, SKILL_SELECTORS
from core.transport.dev_transport_config import SKILLS, RESPONSE_SELECTORS, POSTPROCESSORS

class RabbitMQTransportGatewey(AbstractTransportGateway):
    _component_names: List[str]
    _producer_connection: SelectConnection
    _producer_channel: Channel
    _consumer_connection: SelectConnection
    _consumer_channel: Channel
    _processed_tasks: Dict[dict]
    _processed_events: Dict[asyncio.Event]

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._component_names = [component['name'] for component in itertools.chain[ANNOTATORS, SKILL_SELECTORS, SKILLS,
                                                                                    RESPONSE_SELECTORS, POSTPROCESSORS]]

        #connection_parameters = pika.ConnectionParameters(host=RABBIT_MQ['host'], port=RABBIT_MQ['PORT'])
        #self._producer_connection = pika.SelectConnection(connection_parameters)
        #self._consumer_connection = pika.SelectConnection(connection_parameters)
        #self._producer_channel = self._producer_connection.channel()
        #self._consumer_channel = self._consumer_connection.channel()

    def _connect_producer(self, parameters) -> SelectConnection:
        pass

    def _on_connect_producer(self, connection: SelectConnection) -> None:
        pass

    def _on_open_producer_channel(self, channel: Channel) -> None:
        pass

    def _connect_consumer(self, parameters) -> SelectConnection:
        pass

    def _on_connect_consumer(self, connection: SelectConnection) -> None:
        pass

    def _on_open_consumer_channel(self, channel: Channel) -> None:
        pass
