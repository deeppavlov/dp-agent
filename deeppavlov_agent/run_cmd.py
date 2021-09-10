import asyncio
import os
from logging import getLogger

import hydra
import sentry_sdk
from aioconsole import ainput
from omegaconf import DictConfig

from .setup_agent import setup_agent

logger = getLogger(__name__)

sentry_sdk.init(os.getenv('DP_AGENT_SENTRY_DSN'))


async def message_processor(register_msg):
    user_id = await ainput('Provide user id: ')
    while True:
        msg = await ainput(f'You ({user_id}): ')
        msg = msg.strip()
        if msg:
            response = await register_msg(utterance=msg, user_external_id=user_id, user_device_type='cmd',
                                          location='lab', channel_type='cmd_client',
                                          deadline_timestamp=None, require_response=True)
            print('Bot: ', response['dialog'].utterances[-1].text)


@hydra.main(config_path=".", config_name="settings")
def run_cmd(cfg: DictConfig):
    agent, session, workers = setup_agent(
        cfg.agent.pipeline_config,
        cfg.agent.db_config,
    )
    loop = asyncio.get_event_loop()
    loop.set_debug(cfg.agent.debug)
    future = asyncio.ensure_future(message_processor(agent.register_msg))
    for i in workers:
        loop.create_task(i.call_service(agent.process))
    try:
        loop.run_until_complete(future)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
        raise e
    finally:
        future.cancel()
        if session:
            loop.run_until_complete(session.close())
        loop.stop()
        loop.close()


if __name__ == '__main__':
    run_cmd()
