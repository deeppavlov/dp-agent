from agent_orange.connectors.formatters.deeppavlov import format_dp_ner


formatters_map = {
    'deeppavlov_ner': {
        'formatter': format_dp_ner,
        'description': 'Adapter to DeepPavlov named entity recognition models',
        'default_caller': 'simple_http_caller'
    }
}
