from typing import Dict


def http_api_output_formatter(payload: Dict):
    return {
        'dialog_id': payload['dialog_id'],
        'utt_id': payload['utterances'][-1]['utt_id'],
        'user_id': payload['human']['user_external_id'],
        'response': payload['utterances'][-1]['text'],
        'attributes': payload['utterances'][-1].get('attributes', {})
    }


def http_debug_output_formatter(payload: Dict):
    result = {
        'dialog_id': payload['dialog_id'],
        'utt_id': payload['utterances'][-1]['utt_id'],
        'user_id': payload['human']['user_external_id'],
        'response': payload['utterances'][-1]['text'],
        'active_skill': payload['utterances'][-1]['active_skill'],
        'attributes': payload['utterances'][-1].get('attributes', {})
    }
    if payload["utterances"][-2].get("attributes", {}).get("debug_output", False):
        result["debug_output"]["hypotheses"] = payload['utterances'][-2]['hypotheses']
        result["debug_output"]["annotations"] = payload['utterances'][-2]['annotations']

    return result
