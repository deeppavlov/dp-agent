from typing import Dict, Any, List
import json
import random
import copy


def base_last_utterances_formatter_in(dialog: Dict, model_args_names=("x",)):
    return [{model_args_names[0]: [dialog["utterances"][-1]["text"]]}]


def base_utterances_formatter_in(dialog: Dict, model_args_names=("x",)):
    return [{model_args_names[0]: [[utt["text"] for utt in dialog["utterances"]]]}]


def base_hypotheses_formatter_in(dialog: Dict, model_args_names=("x",)):
    return [{model_args_names[0]: [i["text"]]} for i in dialog["utterances"][-1]["hypotheses"]]


def all_hypotheses_formatter_in(dialog: Dict):
    return [{"hypotheses": dialog["utterances"][-1]["hypotheses"]}]


def chitchat_formatter_in(dialog: Dict, model_args_names=("q",)):
    return [{model_args_names[0]: [dialog["utterances"][-1]["text"]]}]


def odqa_formatter_in(dialog: Dict, model_args_names=("question_raw",)):
    return [{model_args_names[0]: [dialog["utterances"][-1]["text"]]}]


def chitchat_example_formatter_in(
    dialog: Dict, model_args_names=("utterances", "annotations", "u_histories", "dialogs")
):
    return {
        model_args_names[0]: [dialog["utterances"][-1]["text"]],
        model_args_names[1]: [dialog["utterances"][-1]["annotations"]],
        model_args_names[2]: [[utt["text"] for utt in dialog["utterances"]]],
        model_args_names[3]: [dialog],
    }


def ner_formatter_out(payload: List):
    if len(payload) == 2:
        return {"tokens": payload[0], "tags": payload[1]}
    else:
        raise ValueError("Payload doesn't contain all required fields")


def sentiment_formatter_out(payload: List):
    return payload


def rule_based_selector_formatter_out(payload: List):
    if payload:
        print(f"rule_based_selector chooses {payload}")
        return payload
    else:
        raise ValueError("Empty payload provided")


def neuro_chitchat_odqa_selector_formatter_out(payload: List):
    if payload:
        class_name = payload[0]
        if class_name in ["chit-chat"]:
            response = ["ranking_chitchat_2stage"]
        else:
            response = ["odqa"]
        print(f"neuro_chitchat_odqa_selector chooses {payload}")
        return response
    else:
        raise ValueError("Empty payload provided")


def add_confidence_formatter_out(payload: List, confidence=0.5):
    if payload:
        return [{"text": payload[0], "confidence": 0.5}]
    else:
        raise ValueError("Empty payload provided")


def chitchat_example_formatter_out(payload: List):
    if len(payload) == 3:
        return [{"text": payload[0], "confidence": payload[1], "name": payload[2]}]
    else:
        raise ValueError("Payload doesn't contain all required fields")


def ranking_chitchat_formatter_in(dialog: Dict) -> List:
    return [
        {
            "last_utterances": dialog["utterances"][-1]["text"],
            "utterances_histories": [json.dumps([i["text"] for i in dialog["utterances"]], ensure_ascii=False)],
        }
    ]


def confidence_formatter_out(payload):
    return [{"text": payload[0], "confidence": payload[1]}]


noanswers = [
    "Извините, я не знаю ответ на это",
    "Я хочу ответить, но моих знаний пока недостаточно",
    "Жаль, что мне нечего сказать в ответ, но я учусь и когда-нибудь у меня будет подходящий ответ",
    "Мне нечего сказать на это",
    "Мне бы кто-нибудь помог ответить на это",
    "Я пока не готов дать ответ",
]


def add_confidence_with_noanswer_formatter_out(payload: List, confidence=0.5):
    next_payload = copy.deepcopy(payload)
    next_payload[0] = next_payload[0] if next_payload[0] else random.choice(noanswers)
    return add_confidence_formatter_out(payload=next_payload, confidence=confidence)


def confidence_with_noanswer_formatter_out(payload: List):
    next_payload = copy.deepcopy(payload)
    next_payload[0] = next_payload[0] if next_payload[0] else random.choice(noanswers)
    return confidence_formatter_out(payload=next_payload)
