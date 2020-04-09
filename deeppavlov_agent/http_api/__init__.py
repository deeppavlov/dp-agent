# This module implements http api, which allows to communicate with Agent

from .api import init_app

from ..base_settings import (
    TIME_LIMIT, OUTPUT_FORMATTER, DEBUG_OUTPUT_FORMATTER, DEBUG, RESPONSE_LOGGER
)

from ..setup_agent import setup_agent
from ..core.log import LocalResponseLogger


def app_factory():
    agent, session, workers = setup_agent()
    response_logger = LocalResponseLogger(RESPONSE_LOGGER)
    if DEBUG:
        output_formatter = DEBUG_OUTPUT_FORMATTER
    else:
        output_formatter = OUTPUT_FORMATTER

    app = init_app(
        agent=agent, session=session, consumers=workers,
        logger_stats=response_logger, output_formatter=output_formatter,
        debug=DEBUG, response_time_limit=TIME_LIMIT
    )

    return app
