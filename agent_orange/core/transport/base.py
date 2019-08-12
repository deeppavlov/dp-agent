from abc import abstractmethod
from typing import List, Callable, TypeVar, Union, Dict, Any, Awaitable


class TransportGatewayBase:
    _from_service_callback: Awaitable

    def __init__(self, from_service_callback: Awaitable, *args, **kwargs):
        super(TransportGatewayBase, self).__init__(*args, **kwargs)
        self._from_service_callback = from_service_callback

    @abstractmethod
    async def send_to_service(self, service: str, dialog_state: dict) -> None:
        pass


# TODO: Make service caller async
class ServiceCallerBase:
    _config: dict
    _service_name: str
    _formatter: Callable[[Union[List[Dict], Any], bool], Union[Any, List[Any]]]

    def __init__(self,
                 config: dict,
                 formatter: Callable[[Union[List[Dict], Any], bool], Union[Any, List[Any]]]) -> None:

        self._config = config
        self._service_name = config['service']['name']
        self._formatter = formatter

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
