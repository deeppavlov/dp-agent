from typing import Optional

from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase
from core.transport.adapters.rabbitmq import RabbitMQTransportGateway, RabbitMQTransportConnector


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

    def __init__(self, config: dict) -> None:
        transport_type = config['transport']['type']
        gateway_cls = ADAPTERS_MAP[transport_type]['gateway']
        self._gateway = gateway_cls(config=config)

    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        return await self._gateway.process(service, dialog_state)


class Service:
    _caller: ServiceCallerBase
    _connector: TransportConnectorBase

    def __init__(self, config: dict, service_caller: ServiceCallerBase) -> None:
        self._caller = service_caller
        transport_type = config['transport']['type']
        connector_cls = ADAPTERS_MAP[transport_type]['connector']
        self._connector = connector_cls(config=config, service_caller=self._caller)
