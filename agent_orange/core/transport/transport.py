import asyncio
from typing import Awaitable
from logging import getLogger

from agent_orange.core.transport.base import TTransportGateway, TServiceCaller, TTransportConnector
from agent_orange.core.transport.connectors.rabbitmq import RabbitMQTransportGateway, RabbitMQTransportConnector


logger = getLogger(__name__)

ADAPTERS_MAP = {
    'rabbitmq': {
        'gateway': RabbitMQTransportGateway,
        'connector': RabbitMQTransportConnector
    }
}


# TODO: implement services health checking
# TODO: implement stateful services load balancing
class TransportBus:
    _gateway: TTransportGateway
    _loop: asyncio.AbstractEventLoop

    def __init__(self, config: dict, callback: Awaitable) -> None:
        transport_type = config['transport']['type']
        logger.info(f'Initiating transport bus, transport type: {transport_type}')

        gateway_cls = ADAPTERS_MAP[transport_type]['gateway']
        self._gateway = gateway_cls(config=config, callback=callback)

        self._loop = asyncio.get_event_loop()

    async def process(self, service: str, dialog_state: dict) -> None:
        await self._loop.create_task(self._gateway.process(service, dialog_state))


class Service:
    _caller: TServiceCaller
    _connector: TTransportConnector

    def __init__(self, config: dict, service_caller: TServiceCaller) -> None:
        self._caller = service_caller
        transport_type = config['transport']['type']
        connector_cls = ADAPTERS_MAP[transport_type]['connector']
        self._connector = connector_cls(config=config, service_caller=self._caller)
