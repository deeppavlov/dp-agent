import argparse
import asyncio
from copy import deepcopy

from core.transport.config import config as agent_config
from core.transport.transport import TransportBus


parser = argparse.ArgumentParser()
parser.add_argument('-n', '--name', default='fizz_buzz', help='agent name', type=str)
parser.add_argument('-s', '--service', default='foo', help='service name', type=str)
parser.add_argument('-t', '--timeout', default=8.0, help='transport timeout', type=float)


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


async def send(transport_bus: TransportBus, service: str, task: dict) -> None:
    result = await transport_bus.process(service=service, dialog_state=task)
    result = result or task
    print(f'TEST RESULT: {result}')


async def test(transport_bus: TransportBus, agent_name: str, service_name: str) -> None:
    test_case = [
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 3.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 3.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 3.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 3.0, 'utterance': 'utt'}},
        {'task': {'agent_name': agent_name, 'service': service_name, 'sleep_time': 3.0, 'utterance': 'utt'}}
    ]

    print(f'Test tasks:\n' + '\n'.join([str(task) for task in test_case]))
    tasks = [send(transport_bus, task['task']['service'], task) for task in test_case]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    args = parser.parse_args()
    agent_name = args.name
    service_name = args.service
    timeout = args.timeout

    conf = deepcopy(agent_config)
    conf['agent']['name'] = agent_name
    conf['transport']['timeout_sec'] = timeout

    mock_agent = TransportBus(config=conf)

    loop = asyncio.get_event_loop()
    loop.create_task(test(mock_agent, agent_name, service_name))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
