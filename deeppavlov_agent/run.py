"""

This module is now obsolete. Delete it or move hydra decorators here to be able to use it.

"""

import hydra
from omegaconf import DictConfig

from .run_cmd import run_cmd
from .run_http import run_http
from .run_tg import run_telegram

CHANNELS = {
    "cmd": run_cmd,
    "http": run_http,
    "telegram": run_telegram,
}


@hydra.main(config_path=".", config_name="settings")
def main(cfg: DictConfig):
    run_channel = CHANNELS[cfg.agent.channel]
    run_channel(cfg)


if __name__ == "__main__":
    main()
