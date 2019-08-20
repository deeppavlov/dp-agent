from connectors.formatters.deeppavlov import *
from connectors.formatters.agent import *

formatters_map = {
    'deeppavlov_ner': {
        'formatter': format_dp_ner,
        'description': 'Adapter to DeepPavlov named entity recognition models',
        'default_caller': 'simple_http_caller'
    },
    'deeppavlov_ner_stand': {
        'formatter': format_dp_ner_stand,
        'description': 'Adapter to DeepPavlov named entity recognition models, demo stand API',
        'default_caller': 'simple_http_caller'
    },
    'deeppavlov_odqa_stand': {
        'formatter': format_dp_odqa_stand,
        'description': 'Adapter to DeepPavlov ODQA models, demo stand API',
        'default_caller': 'simple_http_caller'
    },
    'agent_ranking_chitchat_prep': {
        'formatter': format_agent_ranking_chitchat_prep,
        'description': 'Adapter to legacy Agent ranking chitchat',
        'default_caller': 'simple_http_caller'
    },
    'agent_chitchat_odqa_selector': {
        'formatter': format_chitchat_odqa_selector,
        'description': 'Adapter to legacy Agent chitchat-ODQA skill selector',
        'default_caller': 'simple_http_caller'
    },
    'agent_max_conf_response_selector': {
        'formatter': max_conf_response_selector,
        'description': 'Script implementation of selection from agent skills responses by max confidence criteria',
        'default_caller': 'test_python_caller'
    },
    'agent_test_response_formatter': {
        'formatter': test_response_formatter,
        'description': 'Test response formatter script',
        'default_caller': 'test_python_caller'
    }
}
