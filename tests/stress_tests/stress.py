import asyncio
import bisect
import logging
import statistics
import random
import requests
from collections import defaultdict
from datetime import datetime
from logging import config as log_config
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from core.agent import TIMEOUT_MESSAGE
from core.config import get_config
from core.transport import transport_map
from core.transport.base import TChannelGateway
from tests.stress_tests.test_config import test_config

loop = asyncio.get_event_loop()


class StressTestConnector:
    def __init__(self, config: dict) -> None:
        self._channel_id = 'tests'
        self._infer_is_successful = True
        self._user_ids = list()

        config['channel'] = config['channels'][self._channel_id] = {'id': self._channel_id}
        transport_type = config['transport']['type']
        gateway_cls = transport_map[transport_type]['channel']

        self._responses_left = 0
        self._got_all_responses = asyncio.Event()
        self._gateway: TChannelGateway = gateway_cls(config=config, to_channel_callback=self.send_to_channel)
        self._utterance_generator = UtteranceGenerator(test_config['dialogs_url'])

    def run_test(self, batch_size: int, utt_length: int = 5, infers_num: int = 1) -> Tuple[int, float, float]:
        results = list()
        for _ in range(infers_num):
            utters_list = [self._utterance_generator(utt_length) for _ in range(batch_size)]
            self._user_ids = [str(uuid4()) for _ in range(batch_size)]
            self._responses_left = batch_size
            self._got_all_responses.clear()
            self._infer_is_successful = True
            results.append(loop.run_until_complete(self._infer_data(utters_list)))

        passed, await_times = list(zip(*results))
        faults_num = passed.count(False)
        await_times = [infer[1] for infer in results if infer[0] is True]

        await_avg = statistics.mean(await_times) if await_times else 0
        await_std = statistics.stdev(await_times) if len(await_times) >= 2 else 0

        return faults_num, await_avg, await_std

    async def _infer_data(self, utterances: List[str]) -> Tuple[bool, float]:
        time_begin = loop.time()
        for user_id, utterance in zip(self._user_ids, utterances):
            loop.create_task(self._gateway.send_to_agent(utterance=utterance,
                                                         channel_id=self._channel_id,
                                                         user_id=user_id,
                                                         reset_dialog=False))
        try:
            await asyncio.wait_for(self._got_all_responses.wait(), timeout=test_config['infer_timeout'])
        except asyncio.TimeoutError:
            self._infer_is_successful = False

        return self._infer_is_successful, loop.time() - time_begin

    async def send_to_channel(self, user_id: str, response: str) -> None:
        if response == TIMEOUT_MESSAGE:
            self._infer_is_successful = False

        if user_id in self._user_ids:
            self._responses_left -= 1

        if self._responses_left == 0:
            self._got_all_responses.set()


class UtteranceGenerator:
    def __init__(self, dialogs_url: str) -> None:
        dialogs_file_path = Path(__file__).resolve().parent / Path(dialogs_url).name

        if not dialogs_file_path.is_file():
            dialogs = requests.get(dialogs_url)
            dialogs.raise_for_status()
            with dialogs_file_path.open('w') as dialogs_file:
                dialogs_file.write(dialogs.text)

        with dialogs_file_path.open('r') as f:
            dialogs_str: str = f.read()
            self._examples = defaultdict(set)

            tokens = dialogs_str.replace('\n\n', ' ').replace('\n', ' ').split(' ')
            replicas = [replica for dialog in dialogs_str.split('\n\n') for replica in dialog.split('\n')]
            dialogs = [dialog.replace('\n', ' ') for dialog in dialogs_str.split('\n\n')]

            for token in tokens:
                self._examples[len(token)].add(token)

            for repl in replicas:
                self._examples[len(repl)].add(repl)

            for dial in dialogs:
                self._examples[len(dial)].add(dial)

            for key, value in self._examples.items():
                self._examples[key] = list(self._examples[key])

            self._indexes = list(self._examples.keys())
            self._indexes.sort()

    def __call__(self, symbols_num: int) -> str:
        i = bisect.bisect_right(self._indexes, symbols_num)
        substring_symbols_num = self._indexes[i - 1] if i > 0 else 1
        substring = random.choice(self._examples.get(substring_symbols_num, ['!']))
        symbols_num_delta = symbols_num - substring_symbols_num

        if symbols_num_delta < 1:
            result = substring
        elif symbols_num_delta == 1:
            result = f'{substring}{self.__call__(symbols_num_delta)}'
        else:
            result = f'{substring} {self.__call__(symbols_num_delta - 1)}'

        return result


def main():
    root_dir = Path(__file__).resolve().parents[2]

    config = get_config(root_dir / test_config['config_path'])

    logs_dir = Path(__file__).resolve().parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

    test_config['logging']['handlers']['log_to_file']['filename'] = logs_dir / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')}_test.log"
    log_config.dictConfig(test_config["logging"])
    log = logging.root.manager.loggerDict['stress_logger']
    channel_connector: StressTestConnector = StressTestConnector(config)
    for test in test_config['tests']:
        log.info(f'Starting {test["test_name"]}')

        batch_size = test['batch_size']
        utt_length = test['utt_length']
        infers_num = test['infers_num']

        batch_size = list(range(batch_size, batch_size + 1, 1)) if isinstance(batch_size, int) else list(batch_size)
        utt_length = list(range(utt_length, utt_length + 1, 1)) if isinstance(utt_length, int) else list(utt_length)
        infers_num = list(range(infers_num, infers_num + 1, 1)) if isinstance(infers_num, int) else list(infers_num)

        test_grid = [(bs, ul, inum) for bs in batch_size for ul in utt_length for inum in infers_num]

        for bs, ul, inum in test_grid:
            faults_num, await_avg, await_std = channel_connector.run_test(bs, ul, inum)

            log.info(f'batch_size: {bs}, utt_length: {ul}, infers_num: {inum}, '
                     f'FAULTS: {faults_num}, AVG_TIME: {await_avg}, STD {await_std}')


if __name__ == '__main__':
    main()
