from core.transport.gateways.rabbitmq import RabbitMQAgentGateway, RabbitMQServiceGateway, RabbitMQChannelGateway
from core.connectors import ServiceGatewayHTTPConnector

gateways_map = {
    'rabbitmq': {
        'agent': RabbitMQAgentGateway,
        'service': RabbitMQServiceGateway,
        'channel': RabbitMQChannelGateway
    }
}

connectors_map = {
    'http': ServiceGatewayHTTPConnector
}