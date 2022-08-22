import os
from logging import getLogger

import sentry_sdk
from omegaconf import DictConfig

from .channels.telegram.bot import run_tg
from .setup_agent import setup_agent

logger = getLogger(__name__)
sentry_sdk.init(os.getenv("DP_AGENT_SENTRY_DSN"))


def run_telegram(cfg: DictConfig):
    agent, session, workers = setup_agent(cfg.agent)
    try:
        run_tg(cfg.agent.telegram_token, cfg.agent.telegram_proxy, agent)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
    finally:
        session.close()
        for i in workers:
            i.cancel()
