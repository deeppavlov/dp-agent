from abc import abstractmethod
from typing import List, Callable, TypeVar


class TransportGatewayBase:
    _callback: Callable[[dict], None]

    def __init__(self, callback: Callable[[dict], None], *args, **kwargs):
        super(TransportGatewayBase, self).__init__(*args, **kwargs)
        self._callback = callback

    @abstractmethod
    async def process(self, service: str, dialog_state: dict) -> None:
        pass


# TODO: think, if we need to isolate ServiceCaller to separate process
class ServiceCallerBase:
    @abstractmethod
    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        pass


class TransportConnectorBase:
    _service_caller: ServiceCallerBase

    def __init__(self, service_caller: ServiceCallerBase, *args, **kwargs) -> None:
        super(TransportConnectorBase, self).__init__(*args, **kwargs)
        self._service_caller = service_caller

    def _infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        return self._service_caller.infer(dialog_states_batch)


TTransportGateway = TypeVar('TTransportGateway', bound='TransportGatewayBase')
TServiceCaller = TypeVar('TServiceCaller', bound='ServiceCallerBase')
TTransportConnector = TypeVar('TTransportConnector', bound='TransportConnectorBase')
