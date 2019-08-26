from core.transport.connectors.rabbitmq import RabbitMQAgentGateway, RabbitMQServiceGateway


transport_map = {
    'rabbitmq': {
        'agent': RabbitMQAgentGateway,
        'service': RabbitMQServiceGateway
    }
}