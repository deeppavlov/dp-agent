import json
import logging
import os

import yaml

from .core.agent import Agent
from .core.connectors import EventSetOutputConnector
from .core.log import LocalResponseLogger
from .core.pipeline import Pipeline
from .core.service import Service
from .parse_config import PipelineConfigParser
from .utils import config_tools


def merge_two_configs(d1, d2):
    for k, v in d2.items():
        if k in d1:
            if isinstance(v, dict) and isinstance(d1[k], dict):
                merge_two_configs(d1[k], v)
            else:
                d1[k] = v
        else:
            d1[k] = v


def setup_agent(agent_config):
    with open(agent_config.db_config, "r") as db_config:
        if agent_config.db_config.endswith(".json"):
            db_data = json.load(db_config)
        elif agent_config.db_config.endswith(".yml"):
            db_data = yaml.load(db_config, Loader=yaml.FullLoader)
        else:
            raise ValueError(
                f"unknown format for db_config file: {agent_config.db_config}"
            )

    if db_data.pop("env", False):
        for k, v in db_data.items():
            db_data[k] = os.getenv(v)

    db_class = config_tools.import_class(agent_config.db_class)
    db = db_class(**db_data)

    sm_class = config_tools.import_class(agent_config.state_manager_class)
    sm = sm_class(db.get_db())
    # if pipeline_configs:
    #     pipeline_data = {}
    #     for name in pipeline_configs:
    #         with open(name, 'r') as pipeline_config:
    #             if name.endswith('.json'):
    #                 merge_two_configs(pipeline_data, json.load(pipeline_config))
    #             elif name.endswith('.yml'):
    #                 merge_two_configs(pipeline_data, yaml.load(pipeline_config, Loader=yaml.FullLoader))
    #             else:
    #                 raise ValueError(f'unknown format for pipeline_config file from command line: {name}')
    #
    # else:
    with open(agent_config.pipeline_config, "r") as pipeline_config_f:
        if agent_config.pipeline_config.endswith(".json"):
            pipeline_data = json.load(pipeline_config_f)
        elif agent_config.pipeline_config.endswith(".yml"):
            pipeline_data = yaml.load(pipeline_config_f, Loader=yaml.FullLoader)
        else:
            raise ValueError(
                f"unknown format for pipeline_config file from setitngs: {agent_config.pipeline_config}"
            )

    pipeline_config = PipelineConfigParser(sm, pipeline_data)

    input_srv = Service("input", None, sm.add_human_utterance, 1, ["input"])
    responder_srv = Service(
        "responder",
        EventSetOutputConnector("responder").send,
        sm.save_dialog,
        1,
        ["responder"],
    )

    last_chance_srv = None
    if not agent_config.overwrite_last_chance:
        last_chance_srv = pipeline_config.last_chance_service
    timeout_srv = None
    if not agent_config.overwrite_timeout:
        timeout_srv = pipeline_config.timeout_service

    pipeline = Pipeline(
        pipeline_config.services, input_srv, responder_srv, last_chance_srv, timeout_srv
    )

    response_logger = LocalResponseLogger(agent_config.enable_response_logger)

    wf_class = config_tools.import_class(agent_config.workflow_manager_class)
    agent = Agent(pipeline, sm, wf_class(), response_logger=response_logger)
    if pipeline_config.gateway:
        pipeline_config.gateway.on_channel_callback = agent.register_msg
        pipeline_config.gateway.on_service_callback = agent.process

    return agent, pipeline_config.session, pipeline_config.workers
