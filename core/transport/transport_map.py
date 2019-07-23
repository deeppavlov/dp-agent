from core.transport.gateway import *

_map = {
    'rabbitmq': {
        'gateway': AbstractTransportGateway,
        'connector': AbstractTransportConnector
    }
}


def get_transport_gateway(transport_solution: str) -> AbstractTransportGateway:
    return _map[transport_solution]['gateway']


def get_transport_connector(transport_solution: str) -> AbstractTransportConnector:
    return _map[transport_solution]['connector']
