import argparse
import asyncio
from datetime import datetime
from copy import deepcopy

from core.transport.config import config as agent_config
from core.transport.transport import TransportBus


parser = argparse.ArgumentParser()
parser.add_argument('-n', '--name', default='fizz_buzz', help='agent name', type=str)
parser.add_argument('-s', '--service', default='foo', help='service name', type=str)


STATE_EXAMPLE = {
    'task': {
        'agent_name': '',
        'service': '',
        'sleep_time': 0.0,
        'utterance': ''
    },
    'response': {
        'agent_name': '',
        'service': '',
        'service_instance_id': '',
        'batch_id': '',
        'sleep_time': 0.0,
        'response': ''
    }
}


class MockAgent:
    _transport_bus: TransportBus
    _loop: asyncio.AbstractEventLoop

    def __init__(self, config: dict) -> None:
        self._transport_bus = TransportBus(config=config, callback=self.callback)
        self._loop = asyncio.get_event_loop()

    @staticmethod
    async def callback(dialog_state: dict) -> None:
        current_time = datetime.now()
        print(f'RECEIVED STATE {str(current_time)} {str(dialog_state)}')

    async def send(self, dialog_state: dict) -> None:
        await self._transport_bus.process(service=dialog_state['task']['service'], dialog_state=dialog_state)


async def test(mock_agent: MockAgent, agent_name: str, service_name: str) -> None:
    test_case = [
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 4.0, 'utterance': 'utt'}}
    ]

    print(f'Test tasks:\n' + '\n'.join([str(task) for task in test_case]))
    tasks = [mock_agent.send(task) for task in test_case]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    args = parser.parse_args()
    agent_name = args.name
    service_name = args.service

    conf = deepcopy(agent_config)
    conf['agent']['name'] = agent_name

    mock_agent = MockAgent(config=conf)

    loop = asyncio.get_event_loop()
    loop.create_task(test(mock_agent, agent_name, service_name))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
