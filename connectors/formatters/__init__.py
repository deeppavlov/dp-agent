from connectors.formatters.deeppavlov import format_dp_ner
from connectors.formatters.agent import format_agent_ranking_chitchat_prep

formatters_map = {
    'deeppavlov_ner': {
        'formatter': format_dp_ner,
        'description': 'Adapter to DeepPavlov named entity recognition models',
        'default_caller': 'simple_http_caller'
    },
    'agent_ranking_chitchat_prep': {
        'formatter': format_agent_ranking_chitchat_prep,
        'description': 'Adapter to legacy Agent ranking chitchat',
        'default_caller': 'simple_http_caller'
    }
}
