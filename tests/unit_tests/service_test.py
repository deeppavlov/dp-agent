from typing import List

from core.transport.config import config
from core.transport.transport import Service
from core.transport.base import ServiceCallerBase


class MockServiceCaller(ServiceCallerBase):
    def infer(self, dialog_states_batch: List[dict]) -> None:
        pass


service = Service(config=config, service_caller=MockServiceCaller())
