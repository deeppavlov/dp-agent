AGENT_NAME = 'dp-agent'

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

TRANSPORT_TIMEOUT_SECS = 30

RABBIT_MQ = {
    'host': '127.0.0.1',
    'port': 5672
}

SKILL_CONFIG = {
    'name': 'skill_name'
}
