import os
from logging import getLogger

import hydra
import sentry_sdk
from omegaconf import DictConfig

from .channels.telegram.bot import run_tg
from .setup_agent import setup_agent


logger = getLogger(__name__)
sentry_sdk.init(os.getenv('DP_AGENT_SENTRY_DSN'))


@hydra.main(config_path=".", config_name="settings")
def run_telegram(cfg: DictConfig):
    agent, session, workers = setup_agent(
        cfg.agent.pipeline_config,
        cfg.agent.db_config,
        cfg.agent.overwrite_last_chance,
        cfg.agent.overwrite_timeout,
        cfg.agent.response_logger,
    )
    try:
        run_tg(cfg.agent.telegram_token, cfg.agent.telegram_proxy, agent)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
    finally:
        session.close()
        for i in workers:
            i.cancel()


if __name__ == '__main__':
    run_telegram()
