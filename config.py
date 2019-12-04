from os import getenv

from state_formatters.dp_formatters import *

DB_NAME = getenv('DB_NAME', 'dp_agent')
DB_HOST = getenv('DB_HOST', '127.0.0.1')
DB_PORT = getenv('DB_PORT', 27017)
DB_PATH = getenv('DB_PATH', '/data/db')

MAX_WORKERS = 4

AGENT_ENV_FILE = "agent.env"

SKILLS = [
    {
        "name": "odqa",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2080,
        "endpoint": "model",
        "path": "ru_odqa_infer_wiki",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter_in": odqa_formatter_in,
        "formatter_out": add_confidence_formatter_out
    },
    {
        "name": "chitchat",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2081,
        "endpoint": "model",
        "path": "tfidf_autofaq",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "profile_handler": True,
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter_in": chitchat_formatter_in,
        "formatter_out": add_confidence_formatter_out
    }
]

POST_ANNOTATORS = [
    {
        "name": "bot_ner",
        "label": "ner",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2083,
        "endpoint": "model",
        "formatter_in": base_hypotheses_formatter_in,
        "formatter_out": ner_formatter_out
    },
    {
        "name": "bot_sentiment",
        "label": "sentiment",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2084,
        "endpoint": "model",
        "formatter_in": base_hypotheses_formatter_in,
        "formatter_out": sentiment_formatter_out
    }
]

ANNOTATORS_1 = [
    {
        "name": "ner",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2083,
        "endpoint": "model",
        "path": "ner_rus",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter_in": base_last_utterances_formatter_in,
        "formatter_out": ner_formatter_out
    }
]

ANNOTATORS_2 = [
    {
        "name": "sentiment",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2084,
        "endpoint": "model",
        "path": "rusentiment_cnn",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter_in": base_last_utterances_formatter_in,
        "formatter_out": sentiment_formatter_out
    }
]

ANNOTATORS_3 = []

SKILL_SELECTORS = [
    {
        "name": "chitchat_odqa",
        "protocol": "http",
        "host": "127.0.0.1",
        "port": 2082,
        "endpoint": "model",
        "path": "rusentiment_bigru_superconv",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter_in": base_last_utterances_formatter_in,
        "formatter_out": chitchat_odqa_formatter_out
    }
]

RESPONSE_SELECTORS = []

POSTPROCESSORS = []

DEBUG = True
