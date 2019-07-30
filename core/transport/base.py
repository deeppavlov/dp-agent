from abc import ABCMeta, abstractmethod
from typing import List, Optional


class TransportGatewayBase(metaclass=ABCMeta):
    @abstractmethod
    async def process(self, service: str, dialog_state: dict) -> Optional[dict]:
        pass


# TODO: think, if we need to isolate ServiceCaller to separate process
class ServiceCallerBase(metaclass=ABCMeta):
    @abstractmethod
    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        pass


class TransportConnectorBase(metaclass=ABCMeta):
    _service_caller: ServiceCallerBase

    def __init__(self, service_caller: ServiceCallerBase) -> None:
        self._service_caller = service_caller

    def _infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        return self._service_caller.infer(dialog_states_batch)
