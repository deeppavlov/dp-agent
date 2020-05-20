# This module implements http api, which allows to communicate with Agent

from .api import init_app

from ..settings import (
    TIME_LIMIT, OUTPUT_FORMATTER, DEBUG_OUTPUT_FORMATTER, DEBUG, RESPONSE_LOGGER
)

from ..setup_agent import setup_agent
from ..core.log import LocalResponseLogger


def app_factory(pipeline_configs=None, debug=None, response_time_limit=None):
    agent, session, workers = setup_agent(pipeline_configs)
    response_logger = LocalResponseLogger(RESPONSE_LOGGER)
    if DEBUG:
        output_formatter = DEBUG_OUTPUT_FORMATTER
    else:
        output_formatter = OUTPUT_FORMATTER

    app = init_app(
        agent=agent, session=session, consumers=workers,
        logger_stats=response_logger, output_formatter=output_formatter,
        debug=debug or DEBUG, response_time_limit=response_time_limit or TIME_LIMIT
    )

    return app
