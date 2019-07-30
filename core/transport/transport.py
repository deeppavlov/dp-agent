from typing import Optional

from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase
from core.transport.adapters.rabbitmq import RabbitMQTransportGateway, RabbitMQTransportConnector
from core.transport.z_dev_config import TRANSPORT_TYPE


ADAPTERS_MAP = {
    'rabbitmq': {
        'gateway': RabbitMQTransportGateway,
        'connector': RabbitMQTransportConnector
    }
}


# TODO: implement services health checking
class HealthChecker:
    pass


# TODO: implement stateful services load balancing
class LoadBalancer:
    pass


class TransportBus:
    _gateway: TransportGatewayBase
    _health_checker: HealthChecker
    _load_balancer: LoadBalancer

    def __init__(self) -> None:
        gateway_cls = ADAPTERS_MAP[TRANSPORT_TYPE]['gateway']
        self._gateway = gateway_cls()

    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        return await self._gateway.process(service, dialog_state)


class Service:
    _caller: ServiceCallerBase
    _connector: TransportConnectorBase

    def __init__(self, service_caller: ServiceCallerBase) -> None:
        self._caller = service_caller

        connector_cls = ADAPTERS_MAP[TRANSPORT_TYPE]['connector']
        self._connector = connector_cls(self._caller)
