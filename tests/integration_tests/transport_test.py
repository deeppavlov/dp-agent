import time
from uuid import uuid4
from typing import List
from multiprocessing import Process
from copy import deepcopy

from core.transport.config import config as transport_config
from core.transport.base import ServiceCallerBase
from core.transport.transport import TransportBus, Service


STATE_EXAMPLE = {
    'task': {
        'agent_name': '',
        'skill': '',
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

    def __init__(self, config):
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


class MockService(Process):
    _service: Service

    def __init__(self, config):
        super(MockService, self).__init__()
        self._service = Service(config=config, service_caller=MockServiceCaller(config))

    def run(self) -> None:
        while True:
            pass


transport_config['transport']['timeout_sec'] = 10.0

# agent foo mocking
agent_foo_config = deepcopy(transport_config)
agent_foo_config['agent']['name'] = 'agent_foo'

# agent bar mocking
agent_bar_config = deepcopy(transport_config)
agent_bar_config['agent']['name'] = 'agent_bar'

# service fizz mocking
service_fizz_i1_config = deepcopy(transport_config)
service_fizz_i1_config['service']['name'] = 'fizz'
service_fizz_i1_config['service']['instance_id'] = 'fizz_i1'

service_fizz_i2_config = deepcopy(transport_config)
service_fizz_i2_config['service']['name'] = 'fizz'
service_fizz_i2_config['service']['instance_id'] = 'fizz_i2'

# service buzz mocking
service_buzz_i1_config = deepcopy(transport_config)
service_buzz_i1_config['service']['name'] = 'buzz'
service_buzz_i1_config['service']['instance_id'] = 'buzz_i1'

service_buzz_i2_config = deepcopy(transport_config)
service_buzz_i2_config['service']['name'] = 'buzz'
service_buzz_i2_config['service']['instance_id'] = 'buzz_i2'

