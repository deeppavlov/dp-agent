import argparse
import asyncio
import datetime
import random
import uuid
from pathlib import Path
from typing import Awaitable, Callable, Dict

import yaml

from core.config import get_config
from core.transport import transport_map
from core.transport.base import ChannelConnectorBase, TChannelConnector, TChannelGateway

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


class StressConnector(ChannelConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _user_id: str

    def __init__(self, config: dict, on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:
        super(StressConnector, self).__init__(config=config, on_channel_callback=on_channel_callback)
        self._utterances = {}
        self.successful = {}
        self.event = asyncio.Event()

    async def send_data(self, utters, utters_number) -> None:
        for _ in range(utters_number):
            utterance = random.choice(utters)
            _user_id = str(uuid.uuid4())
            self._utterances[_user_id] = {'send': utterance,
                                          'send_time': datetime.datetime.now()}
            print(f'>> {utterance}')
            loop.create_task(self._on_channel_callback(utterance=utterance,
                                                       channel_id=self._channel_id,
                                                       user_id=_user_id,
                                                       reset_dialog=False))

    async def send_to_channel(self, user_id: str, response: str) -> None:
        print(f'<< {response}')
        utter = self._utterances.pop(user_id)
        utter['resp_time'] = datetime.datetime.now()
        utter['response'] = response
        self.successful[user_id] = utter
        if not self._utterances:
            self.event.set()


def run_channel(config: Dict):
    async def on_channel_message(utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        await _gateway.send_to_agent(utterance=utterance,
                                     channel_id=channel_id,
                                     user_id=user_id,
                                     reset_dialog=reset_dialog)

    async def send_to_channel(user_id: str, response: str) -> None:
        await _channel_connector.send_to_channel(user_id=user_id, response=response)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['channel']

    _gateway: TChannelGateway = gateway_cls(config=config, to_channel_callback=send_to_channel)
    _channel_connector: TChannelConnector = StressConnector(config=config, on_channel_callback=on_channel_message)
    return _channel_connector


async def foo(connector, utters, utters_number):
    await connector.send_data(utters, utters_number)
    await connector.event.wait()
    print(connector.successful)


def main():
    args = parser.parse_args()
    print(args)
    utters_number = args.utters_number
    utters_type = args.utters_type
    if utters_type == '':
        utters = []
        for utter_list in stress_config['utters'].values():
            utters += utter_list
    else:
        utters = stress_config['utters'][utters_type]
    connector = run_channel(config)
    loop.run_until_complete(foo(connector, utters, utters_number))


if __name__ == '__main__':
    main()
