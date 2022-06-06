# This module implements http api, which allows to communicate with Agent

from .api import init_app

from ..setup_agent import setup_agent
from ..utils import config_tools


def app_factory(agent_config):
    agent, session, workers = setup_agent(agent_config)
    response_logger = agent._response_logger
    if agent_config.debug:
        output_formatter_qualname = agent_config.debug_output_formatter
    else:
        output_formatter_qualname = agent_config.output_formatter

    app = init_app(
        agent=agent,
        session=session,
        consumers=workers,
        logger_stats=response_logger,
        output_formatter=config_tools.import_class(output_formatter_qualname),
        debug=agent_config.debug,
        response_time_limit=agent_config.response_time_limit,
        cors=agent_config.cors,
    )

    return app
