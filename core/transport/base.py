from abc import abstractmethod
from typing import List, Callable, TypeVar, Union, Dict, Any, Awaitable


TAgentGateway = TypeVar('TAgentGateway', bound='AgentGatewayBase')
TServiceCaller = TypeVar('TServiceCaller', bound='ServiceCallerBase')
TServiceGateway = TypeVar('TServiceGateway', bound='ServiceGatewayBase')
TChannelConnector = TypeVar('TChannelConnector', bound='ChannelConnectorBase')
TChannelGateway = TypeVar('TChannelGateway', bound='ChannelGatewayBase')


class AgentGatewayBase:
    _on_service_callback: Awaitable
    _on_channel_callback: Awaitable

    def __init__(self, on_service_callback: Awaitable, on_channel_callback: Awaitable, *args, **kwargs):
        super(AgentGatewayBase, self).__init__(*args, **kwargs)
        self._on_service_callback = on_service_callback
        self._on_channel_callback = on_channel_callback

    @abstractmethod
    async def send_to_service(self, service: str, dialog_state: dict) -> None:
        pass

    @abstractmethod
    async def send_to_channel(self, channel_id: str, user_id: str, response: str) -> None:
        pass


# TODO: Make service caller async?
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


class ServiceGatewayBase:
    _service_caller: TServiceCaller

    def __init__(self, service_caller: ServiceCallerBase, *args, **kwargs) -> None:
        super(ServiceGatewayBase, self).__init__(*args, **kwargs)
        self._service_caller = service_caller

    def _infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        return self._service_caller.infer(dialog_states_batch)


class ChannelConnectorBase:
    _config: dict
    _channel_id: str
    _on_channel_callback: Awaitable

    def __init__(self, config: dict, on_channel_callback: Awaitable) -> None:
        self._config = config
        self._channel_id = self._config['channel']['id']
        self._on_channel_callback = on_channel_callback

    @abstractmethod
    async def send_to_channel(self, user_id: str, response: str) -> None:
        pass


class ChannelGatewayBase:
    _to_channel_callback: Awaitable

    def __init__(self, to_channel_callback: Awaitable, *args, **kwargs) -> None:
        super(ChannelGatewayBase, self).__init__(*args, **kwargs)
        self._to_channel_callback = to_channel_callback

    @abstractmethod
    async def send_to_agent(self, utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        pass
