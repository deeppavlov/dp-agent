from core.transport.gateways.rabbitmq import RabbitMQAgentGateway, RabbitMQServiceGateway, RabbitMQChannelGateway
from core.connectors import ServiceGatewayHTTPConnector
from core.log import init_logger


STATE_API_VERSION = "0.12"

init_logger()

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