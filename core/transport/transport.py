from core.transport.base import TransportGatewayBase, TransportConnectorBase, ServiceCallerBase
from core.transport.adapters.rabbitmq import RabbitMQTransportGateway, RabbitMQTransportConnector


ADAPTERS_MAP = {
    'rabbitmq': {
        'gateway': RabbitMQTransportGateway,
        'connector': RabbitMQTransportConnector
    }
}


class HealthChecker:
    pass


class LoadBalancer:
    pass


class TransportBus:
    _gateway: TransportGatewayBase
    _health_checker: HealthChecker
    _load_balancer: LoadBalancer
    pass


class Service:
    _caller: ServiceCallerBase
    _connector: ServiceCallerBase
    pass
