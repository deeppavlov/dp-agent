import sys
import logging

import hydra
from omegaconf import DictConfig

import deeppavlov_agent.log as log
from .run_cmd import run_cmd
from .run_http import run_http
from .run_tg import run_telegram

logger = logging.getLogger("run")

CHANNELS = {
    "cmd": run_cmd,
    "http": run_http,
    "telegram": run_telegram,
}


@hydra.main(config_path=".", config_name="settings")
def main(cfg: DictConfig):
    with log.setup():
        try:
            run_channel = CHANNELS[cfg.agent.channel]
            run_channel(cfg)
        except Exception as e:
            logger.exception(e)
            sys.exit(-1)


if __name__ == "__main__":
    main()
