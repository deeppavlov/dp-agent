import argparse

from .settings import TELEGRAM_TOKEN, TELEGRAM_PROXY
from .core.telegram_client import run_tg
from .setup_agent import setup_agent


def run_telegram(pipeline_configs=None):
    agent, session, workers = setup_agent(pipeline_configs)
    try:
        run_tg(TELEGRAM_TOKEN, TELEGRAM_PROXY, agent)
    finally:
        session.close()
        for i in workers:
            i.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-pl', '--pipeline_config', help='Pipeline config (overwrite value, defined in settings)',
                        type=str, action='append')
    args = parser.parse_args()

    run_telegram(args.pipeline_config)
