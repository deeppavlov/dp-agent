import os
from logging import getLogger

import sentry_sdk
from aiohttp import web
from omegaconf import DictConfig

from .http_api import app_factory

logger = getLogger(__name__)
sentry_sdk.init(os.getenv("DP_AGENT_SENTRY_DSN"))


def run_http(cfg: DictConfig):
    try:
        app = app_factory(cfg.agent)
        web.run_app(app, port=cfg.agent.port)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
        raise e
