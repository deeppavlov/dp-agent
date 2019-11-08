from os import getenv

from state_formatters.dp_formatters import *

DB_NAME = getenv('DB_NAME', 'dp_agent')
DB_HOST = getenv('DB_HOST', '10.11.1.251')
DB_PORT = getenv('DB_PORT', 9001)
DB_PATH = getenv('DB_PATH', '/data/db')

MAX_WORKERS = 4

AGENT_ENV_FILE = "agent.env"

SKILLS = [
    {
        "name": "odqa",
        "protocol": "http",
        "host": "10.11.1.251",
        "port": 9002,
        "endpoint": "model",
        "path": "odqa/ru_odqa_infer_wiki_rubert_noans",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter": odqa_formatter
    },
    {
        "name": "ranking_chitchat_2stage",
        "protocol": "http",
        "host": "10.11.1.251",
        "port": 9003,
        "endpoint": "model",
        "path": "skills/ranking_chitchat_2stage/agent_ranking_chitchat_2staged_tfidf_smn_v4_prep.json",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "profile_handler": True,
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter": ranking_chitchat_formatter
    }
]

ANNOTATORS_1 = [
    {
        "name": "ner",
        "protocol": "http",
        "host": "10.11.1.251",
        "port": 9004,
        "endpoint": "model",
        "path": "ner_rus",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter": ner_formatter
    }
]

ANNOTATORS_2 = [
    {
        "name": "sentiment",
        "protocol": "http",
        "host": "10.11.1.251",
        "port": 9005,
        "endpoint": "model",
        "path": "rusentiment_cnn",
        "env": {
            "CUDA_VISIBLE_DEVICES": ""
        },
        "base_image": "deeppavlov/base-cpu:0.6.1",
        "formatter": sentiment_formatter
    }
]

ANNOTATORS_3 = []

SKILL_SELECTORS = [
    # {
    #     "name": "chitchat_odqa",
    #     "protocol": "http",
    #     "host": "127.0.0.1",
    #     "port": 2082,
    #     "endpoint": "model",
    #     "path": "classifiers/rusentiment_bigru_superconv",
    #     "env": {
    #         "CUDA_VISIBLE_DEVICES": ""
    #     },
    #     "dockerfile": "dockerfile_skill_cpu",
    #     "formatter": chitchat_odqa_formatter
    # }
]

RESPONSE_SELECTORS = []

POSTPROCESSORS = []

DEBUG = True
