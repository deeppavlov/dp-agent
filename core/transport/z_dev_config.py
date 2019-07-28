AGENT_NAME = 'dp-agent'


# services
ANNOTATORS = [
    {
        'name': 'ner',
        'stateful': False
    },
    {
        'name': 'sentiment',
        'stateful': False
    },
    {
        'name': 'obscenity',
        'stateful': False
    }
]

SKILL_SELECTORS = [
    {
        'name': 'chitchat_odqa',
        'stateful': False
    }
]

SKILLS = [
    {
        'name': 'odqa',
        'stateful': False
    },
    {
        'name': 'chitchat',
        'stateful': False
    }
]

RESPONSE_SELECTORS = []

POSTPROCESSORS = []


# transport
TRANSPORT_TYPE = 'rabbitmq'
TRANSPORT_TIMEOUT_SECS = 30

RABBIT_MQ = {
    'host': '127.0.0.1',
    'port': 5672
}


# service instance config
SERVICE_CONFIG = {
    'name': 'skill_name',
    'instance_id': None,
    'remote_url': 'protocol://host:port/endpoint',
    'batch_size': 1,
    'batch_polling_interval_secs': 0.01
}
