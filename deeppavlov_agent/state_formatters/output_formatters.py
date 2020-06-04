from typing import Dict


def http_api_output_formatter(payload: Dict):
    return {
        'dialog_id': payload['dialog_id'],
        'utt_id': payload['utterances'][-1]['utt_id'],
        'user_id': payload['human']['user_external_id'],
        'response': payload['utterances'][-1]['text'],
    }


def http_debug_output_formatter(payload: Dict):
    return {
        'dialog_id': payload['dialog_id'],
        'utt_id': payload['utterances'][-1]['utt_id'],
        'user_id': payload['human']['user_external_id'],
        'response': payload['utterances'][-1]['text'],
        'active_skill': payload['utterances'][-1]['active_skill'],
        'debug_output': payload['utterances'][-2]['hypotheses']
    }
