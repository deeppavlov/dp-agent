import argparse
import asyncio
import random
import logging
from pathlib import Path
from datetime import datetime
from logging import config as log_config
from typing import List, Optional
from uuid import uuid4

import numpy as np
import yaml

from core.agent import TIMEOUT_MESSAGE
from core.config import get_config
from core.transport import transport_map
from core.transport.base import TChannelGateway


def positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f'invalid positive_int value: {value}')
    return ivalue


parser = argparse.ArgumentParser()
parser.add_argument('-b', '--batch-size', help='number of users simultaneously sending a message', type=positive_int)
parser.add_argument('-i', '--infers-num', help='number of infers by which the response time is averaged',
                    type=positive_int, default=5)
parser.add_argument('-t', '--utters-type', type=str, choices={'odqa', 'chitchat'}, default='')


root_dir = Path(__file__).resolve().parents[2]
stress_config_path = root_dir / 'tests/stress_tests/stress_config.yaml'

with stress_config_path.open('r') as f:
    stress_config = yaml.safe_load(f)

config = get_config(root_dir / stress_config['config_path'])

log_config.dictConfig(stress_config["logging"])
log = logging.root.manager.loggerDict['stress_logger']

loop = asyncio.get_event_loop()


class StressConnector:
    def __init__(self, config: dict, phrases_list: List[str]) -> None:
        self._channel_id = 'tests'
        self._wrong_response = False
        config['channel'] = config['channels'][self._channel_id] = {'id': self._channel_id}
        transport_type = config['transport']['type']
        gateway_cls = transport_map[transport_type]['channel']

        self._responses_left = None
        self._event = asyncio.Event()
        self._gateway: TChannelGateway = gateway_cls(config=config, to_channel_callback=self.send_to_channel)
        self._phrases_list = phrases_list

    async def run_test(self, batch_size: int, infers_num: int) -> None:
        faults = 0
        test_durations = []
        for _ in range(infers_num):
            test_duration = await self._infer_data(batch_size)
            if test_duration is None:
                faults += 1
            else:
                test_durations.append(test_duration)
        avg_time = std_time = 0
        if test_durations:
            avg_time = np.average(test_durations)
            std_time = np.std(test_durations)
        log.info(f'batch_size: {batch_size}, infers_num: {infers_num}, FAULTS: {faults}, '
                 f'AVG_TIME: {avg_time:.2f}, STD: {std_time:.2f}')

    async def _infer_data(self, batch_size: int) -> Optional[float]:
        self._wrong_response = False
        utters_list = [(random.choice(self._phrases_list)) for _ in range(batch_size)]
        self._users_list = [str(uuid4()) for _ in range(batch_size)]
        self._responses_left = batch_size
        self._event.clear()
        batch_send_time = datetime.now()
        for user_id, utterance in zip(self._users_list, utters_list):
            loop.create_task(self._gateway.send_to_agent(utterance=utterance,
                                                         channel_id=self._channel_id,
                                                         user_id=user_id,
                                                         reset_dialog=False))
        try:
            await asyncio.wait_for(self._event.wait(), timeout=stress_config['test_timeout'])
        except asyncio.TimeoutError:
            pass
        else:
            if not self._wrong_response:
                test_time = (datetime.now() - batch_send_time).total_seconds()
                return test_time

    async def send_to_channel(self, user_id: str, response: str) -> None:
        self._responses_left -= 1
        if response == TIMEOUT_MESSAGE:
            log.debug('got timeout message')
            self._wrong_response = True
        elif user_id not in self._users_list:
            log.debug('got unexpected user_id')
            self._wrong_response = True
        if self._responses_left == 0 or self._wrong_response is True:
            self._event.set()


def main():
    args = parser.parse_args()
    batch_size = args.batch_size
    utters_type = args.utters_type
    infers_num = args.infers_num
    phrases_list = []
    keys = stress_config['phrases'].keys() if utters_type == '' else [utters_type]
    for key in keys:
        phrases_list += stress_config['phrases'][key]
    _channel_connector: StressConnector = StressConnector(config, phrases_list)
    loop.run_until_complete(_channel_connector.run_test(batch_size, infers_num))


if __name__ == '__main__':
    main()
