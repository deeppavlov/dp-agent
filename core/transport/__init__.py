from core.transport.connectors.rabbitmq import RabbitMQTransportGateway, RabbitMQTransportConnector


transport_map = {
    'rabbitmq': {
        'gateway': RabbitMQTransportGateway,
        'connector': RabbitMQTransportConnector
    }
}