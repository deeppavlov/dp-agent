from core.transport.gateways.rabbitmq import RabbitMQAgentGateway, RabbitMQServiceGateway, RabbitMQChannelGateway
from core.connectors import ServiceGatewayHTTPConnector
from core.log import init_logger


STATE_API_VERSION = "0.12.0"

init_logger()

gateways_map = {
    'AMQP': {
        'agent': RabbitMQAgentGateway,
        'service': RabbitMQServiceGateway,
        'channel': RabbitMQChannelGateway
    }
}

connectors_map = {
    'AMQP': ServiceGatewayHTTPConnector
}
