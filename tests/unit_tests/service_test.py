import time
import argparse
from uuid import uuid4
from typing import List
from copy import deepcopy

from core.transport.config import config as service_config
from core.transport.transport import Service
from core.transport.base import ServiceCallerBase


parser = argparse.ArgumentParser()
parser.add_argument('-s', '--service', default='foo', help='service name', type=str)
parser.add_argument('-i', '--instance', default='bar', help='service instance id', type=str)
parser.add_argument('-b', '--batch-size', default=3, help='batch size', type=int)


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


class MockServiceCaller(ServiceCallerBase):
    _config: dict
    _service_name: str
    _instance_id: str

    def __init__(self, config) -> None:
        self._config = config
        self._service_name = self._config['service']['name']
        self._instance_id = self._config['service']['instance_id']

    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        sleep_time_batch = []
        batch_id = str(uuid4())

        for dialog_state in dialog_states_batch:
            dialog_state['response'] = {}
            dialog_state['response']['agent_name'] = dialog_state['task']['agent_name']
            dialog_state['response']['service'] = self._service_name
            dialog_state['response']['service_instance_id'] = self._instance_id
            dialog_state['response']['batch_id'] = batch_id
            dialog_state['response']['sleep_time'] = dialog_state['task']['sleep_time']
            dialog_state['response']['response'] = f"{dialog_state['task']['utterance']}_responded"
            sleep_time_batch.append(dialog_state['task']['sleep_time'])

        sleep_time = max(sleep_time_batch)
        time.sleep(sleep_time)

        return dialog_states_batch


if __name__ == '__main__':
    args = parser.parse_args()
    service_name = args.service
    instance_id = args.instance
    batch_size = args.batch_size

    conf = deepcopy(service_config)
    conf['service']['name'] = service_name
    conf['service']['instance_id'] = instance_id
    conf['service']['batch_size'] = batch_size

    try:
        service = Service(config=conf, service_caller=MockServiceCaller(conf))
    except KeyboardInterrupt:
        pass
