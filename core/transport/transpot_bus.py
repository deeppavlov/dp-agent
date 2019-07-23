from core.transport.gateway import AbstractTransportGateway
from core.transport.transport_map import get_transport_connector


class HealthChecker:
    pass


class LoadBalancer:
    pass


class TransportBus:
    gateway: AbstractTransportGateway
    health_checker: HealthChecker
    load_balancer: LoadBalancer

    pass



