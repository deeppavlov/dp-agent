# TODO: move response timeout to transport settings
TRANSPORT_SETTINGS = {
    'agent_namespace': 'deeppavlov_agent',
    'agent': {
        'name': 'dp_agent',
        'response_timeout_sec': 120
    },
    'channels': {},
    'transport': {
        'type': 'rabbitmq',
        'rabbitmq': {
            'host': '127.0.0.1',
            'port': 5672,
            'login': 'guest',
            'password': 'guest',
            'virtualhost': '/'
        }
    }
}
