import argparse
import asyncio
import random
import uuid
from collections import defaultdict
from pathlib import Path
from time import time

import yaml
import numpy as np

from core.config import get_config
from core.transport import transport_map
from core.transport.base import TChannelGateway

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--utters-number', help='number of infers to send', type=int)
parser.add_argument('-t', '--utters-type', type=str, choices={'odqa', 'chitchat'}, default='')


root_dir = Path(__file__).resolve().parents[2]
stress_config_path = root_dir / 'tests/stress_tests/stress_config.yaml'

with stress_config_path.open('r') as f:
    stress_config = yaml.safe_load(f)

config = get_config(root_dir / stress_config['config_path'])

channel_id = 'tests'
config['channel'] = config['channels'][channel_id] = {'id': channel_id}

loop = asyncio.get_event_loop()


class StressConnector:
    def __init__(self) -> None:
        self.utterances = defaultdict(dict)
        self.event = asyncio.Event()

        transport_type = config['transport']['type']
        gateway_cls = transport_map[transport_type]['channel']

        self._gateway: TChannelGateway = gateway_cls(config=config, to_channel_callback=self.send_to_channel)

    async def send_data(self, utters, utters_number) -> None:
        for _ in range(utters_number):
            utterance = random.choice(utters)
            _user_id = str(uuid.uuid4())
            self.utterances['request'][_user_id] = {'send': utterance,
                                                    'send_time': time()}
            loop.create_task(self._gateway.send_to_agent(utterance=utterance,
                                                         channel_id=channel_id,
                                                         user_id=_user_id,
                                                         reset_dialog=False))

    async def send_to_channel(self, user_id: str, response: str) -> None:
        utter = self.utterances['request'].pop(user_id)
        utter['resp_time'] = time()
        utter['response'] = response
        self.utterances['response'][user_id] = utter
        if not self.utterances['request']:
            self.event.set()


def process_results(utts):
    resp = utts['response']
    req = utts['request']
    dt = [utt['resp_time'] - utt['send_time'] for utt in resp.values()]
    print(f'{len(req)} errors\nAverage response time: {np.average(dt)}\nStandart deviation: {np.std(dt)}')


async def foo(connector, utters, utters_number):
    await connector.send_data(utters, utters_number)
    try:
        await asyncio.wait_for(connector.event.wait(), timeout=stress_config['test_timeout'])
    except asyncio.TimeoutError:
        print('Timeout error')
    finally:
        process_results(connector.utterances)


def main():
    args = parser.parse_args()
    utters_number = args.utters_number
    utters_type = args.utters_type
    if utters_type == '':
        utters = []
        for utter_list in stress_config['utters'].values():
            utters += utter_list
    else:
        utters = stress_config['utters'][utters_type]
    _channel_connector: StressConnector = StressConnector()
    loop.run_until_complete(foo(_channel_connector, utters, utters_number))


if __name__ == '__main__':
    main()
