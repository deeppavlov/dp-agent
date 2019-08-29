import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Dict

import yaml

from core.config import get_config
from core.transport import transport_map
from core.transport.base import ChannelConnectorBase, TChannelConnector, TChannelGateway

root_dir = Path(__file__).resolve().parents[2]
stress_config_path = root_dir / 'tests/stress_tests/stress_config.yaml'

with stress_config_path.open('r') as f:
    stress_config = yaml.safe_load(f)

config = get_config(root_dir / stress_config['config_path'])

channel_id = 'tests'
config['channel'] = config['channels'][channel_id] = {'id': channel_id}

phrases = stress_config['phrases']

loop = asyncio.get_event_loop()


class StressConnector(ChannelConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _user_id: str

    def __init__(self, config: dict, on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:
        super(StressConnector, self).__init__(config=config, on_channel_callback=on_channel_callback)
        self._loop = asyncio.get_event_loop()
        self._user_id = 'tests'

        loop.run_until_complete(self.send_data(phrases))

    async def send_data(self, phr) -> None:
        if phr:
            utterance = phr.pop()
            print(f'>> {utterance}')
            self._loop.create_task(self._on_channel_callback(utterance=utterance,
                                                             channel_id=self._channel_id,
                                                             user_id=self._user_id,
                                                             reset_dialog=False))
        else:
            loop.stop()

    async def send_to_channel(self, user_id: str, response: str) -> None:
        print(f'<< {response}')
        await self.send_data(phrases)



def run_channel(config: Dict) -> None:
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


run_channel(config)


if __name__ == '__main__':
    loop.run_forever()
