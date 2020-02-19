from typing import Dict, List


def base_last_utterances_formatter_in(dialog: Dict, model_args_names=('x',)):
    return [{model_args_names[0]: [dialog['utterances'][-1]['text']]}]


def base_hypotheses_formatter_in(dialog: Dict, model_args_names=('x',)):
    return [{model_args_names[0]: [i['text']]} for i in dialog['utterances'][-1]['hypotheses']]


def all_hypotheses_formatter_in(dialog: Dict):
    return[{'hypotheses': dialog['utterances'][-1]['hypotheses']}]


def chitchat_formatter_in(dialog: Dict, model_args_names=('q',)):
    return [{model_args_names[0]: [dialog['utterances'][-1]['text']]}]


def odqa_formatter_in(dialog: Dict, model_args_names=('question_raw',)):
    return [{model_args_names[0]: [dialog['utterances'][-1]['text']]}]


def chitchat_example_formatter_in(dialog: Dict,
                                  model_args_names=("utterances", 'annotations', 'u_histories', 'dialogs')):
    return {
        model_args_names[0]: [dialog['utterances'][-1]['text']],
        model_args_names[1]: [dialog['utterances'][-1]['annotations']],
        model_args_names[2]: [[utt['text'] for utt in dialog['utterances']]],
        model_args_names[3]: [dialog]
    }


def ner_formatter_out(payload: List):
    if len(payload) == 2:
        return {'tokens': payload[0],
                'tags': payload[1]}
    else:
        raise ValueError("Payload doesn't contain all required fields")


def sentiment_formatter_out(payload: List):
    return payload


def chitchat_odqa_formatter_out(payload: List):
    if payload:
        class_name = payload[0]
        if class_name in ['speech', 'negative']:
            response = ['chitchat']
        else:
            response = ['odqa']
        return response
    else:
        raise ValueError('Empty payload provided')


def add_confidence_formatter_out(payload: List, confidence=0.5):
    if payload:
        return [{"text": payload[0], "confidence": 0.5}]
    else:
        raise ValueError('Empty payload provided')


def chitchat_example_formatter_out(payload: List):
    if len(payload) == 3:
        return [{"text": payload[0],
                 "confidence": payload[1],
                 "name": payload[2]}]
    else:
        raise ValueError("Payload doesn't contain all required fields")
