import time
from typing import List
from multiprocessing import Process

from core.transport.config import config
from core.transport.base import ServiceCallerBase
from core.transport.transport import TransportBus, Service


STATE_EXAMPLE = {
    'task': {
        'agent_name': None,
        'skill': None,
        'timeout': 0,
        'utterance': None
    },
    'response': {}
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



class MockService(Process):
    def __init__(self, config):
        super(MockService, self).__init__()
        pass
