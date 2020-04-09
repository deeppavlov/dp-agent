import json
import os
import yaml
import logging

from .base_settings import (
    PIPELINE_CONFIG, DB_CONFIG, STATE_MANAGER_CLASS, DB_CLASS,
    WORKFLOW_MANAGER_CLASS, OVERWRITE_LAST_CHANCE, OVERWRITE_TIMEOUT,
    FORMATTERS_MODULE, CONNECTORS_MODULE, RESPONSE_LOGGER
)
from importlib import import_module

from .core.agent import Agent
from .core.connectors import EventSetOutputConnector
from .core.log import LocalResponseLogger
from .core.pipeline import Pipeline
from .core.service import Service
from .parse_config import PipelineConfigParser


def setup_agent():
    user_settings = None
    try:
        user_settings = import_module('settings')
    except ModuleNotFoundError:
        logging.info('settings.py has not found. Default settings are used')

    if user_settings:
        db_config_file = getattr(user_settings, 'DB_CONFIG', None) or DB_CONFIG
        pipeline_config_file = getattr(user_settings, 'PIPELINE_CONFIG', None) or PIPELINE_CONFIG

    with open(db_config_file, 'r') as db_config:
        if db_config_file.endswith('.json'):
            db_data = json.load(db_config)
        elif db_config_file.endswith('.yml'):
            db_data = yaml.load(db_config)
        else:
            raise ValueError('unknown format for db_config')

    if db_data.pop('env', False):
        for k, v in db_data.items():
            db_data[k] = os.getenv(v)

    db = DB_CLASS(**db_data)

    sm = STATE_MANAGER_CLASS(db.get_db())

    with open(pipeline_config_file, 'r') as pipeline_config:
        if pipeline_config_file.endswith('.json'):
            pipeline_data = json.load(pipeline_config)
        elif pipeline_config_file.endswith('.yml'):
            pipeline_data = yaml.load(pipeline_config)
        else:
            raise ValueError('unknown format for pipeline_config')
    pipeline_config = PipelineConfigParser(sm, pipeline_data, CONNECTORS_MODULE, FORMATTERS_MODULE)

    input_srv = Service('input', None, sm.add_human_utterance, 1, ['input'])
    responder_srv = Service('responder', EventSetOutputConnector('responder').send,
                            sm.save_dialog, 1, ['responder'])

    last_chance_srv = None
    if not OVERWRITE_LAST_CHANCE:
        last_chance_srv = pipeline_config.last_chance_service
    timeout_srv = None
    if not OVERWRITE_TIMEOUT:
        timeout_srv = pipeline_config.timeout_service

    pipeline = Pipeline(pipeline_config.services, input_srv, responder_srv, last_chance_srv, timeout_srv)

    response_logger = LocalResponseLogger(RESPONSE_LOGGER)

    agent = Agent(pipeline, sm, WORKFLOW_MANAGER_CLASS(), response_logger=response_logger)
    if pipeline_config.gateway:
        pipeline_config.gateway.on_channel_callback = agent.register_msg
        pipeline_config.gateway.on_service_callback = agent.process

    return agent, pipeline_config.session, pipeline_config.workers
