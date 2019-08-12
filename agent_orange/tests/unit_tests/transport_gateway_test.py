import argparse
import asyncio
from datetime import datetime
from copy import deepcopy

from agent_orange.config import config as agent_config
from agent_orange.core.transport import transport_map
from agent_orange.core.transport.base import TTransportGateway

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
    _loop: asyncio.AbstractEventLoop
    _transport_gateway: TTransportGateway

    def __init__(self, config: dict) -> None:
        self._loop = asyncio.get_event_loop()
        transport_type = config['transport']['type']
        gateway_cls = transport_map[transport_type]['gateway']
        self._transport_gateway = gateway_cls(config=config, from_service_callback=self.get_from_service)

    @staticmethod
    async def get_from_service(partial_dialog_state: dict) -> None:
        current_time = datetime.now()
        print(f'RECEIVED STATE {str(current_time)} {str(partial_dialog_state)}')

    async def send(self, dialog_state: dict) -> None:
        await self._transport_gateway.send_to_service(service=dialog_state['task']['service'],
                                                      dialog_state=dialog_state)


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
    _agent_name = args.name
    _service_name = args.service

    conf = deepcopy(agent_config)
    conf['agent']['name'] = _agent_name

    _mock_agent = MockAgent(config=conf)

    loop = asyncio.get_event_loop()
    loop.create_task(test(_mock_agent, _agent_name, _service_name))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
