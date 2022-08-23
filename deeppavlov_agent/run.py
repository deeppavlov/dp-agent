import logging

import hydra
from omegaconf import DictConfig

from .run_cmd import run_cmd
from .run_http import run_http
from .run_tg import run_telegram


logger = logging.getLogger(__name__)

CHANNELS = {
    "cmd": run_cmd,
    "http": run_http,
    "telegram": run_telegram,
}


@hydra.main(config_path=".", config_name="settings")
def main(cfg: DictConfig):
    try:
        run_channel = CHANNELS[cfg.agent.channel]
        run_channel(cfg)
    except KeyError:
        logger.error(
            f"agent.channel value must be one of: {', '.join(CHANNELS.keys())} (not {cfg.agent.channel})"
        )


if __name__ == "__main__":
    main()
