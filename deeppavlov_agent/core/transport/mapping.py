from .gateways.rabbitmq import RabbitMQAgentGateway, RabbitMQServiceGateway, RabbitMQChannelGateway
from ..connectors import ServiceGatewayHTTPConnector

GATEWAYS_MAP = {
    'AMQP': {
        'agent': RabbitMQAgentGateway,
        'service': RabbitMQServiceGateway,
        'channel': RabbitMQChannelGateway
    }
}

CONNECTORS_MAP = {
    'AMQP': ServiceGatewayHTTPConnector
}
