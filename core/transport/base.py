from typing import List, Callable, TypeVar, Dict, Any


class AgentGatewayBase:
    _on_service_callback: Callable
    _on_channel_callback: Callable

    def __init__(self, on_service_callback: Callable, on_channel_callback: Callable, *args, **kwargs):
        super(AgentGatewayBase, self).__init__(*args, **kwargs)
        self._on_service_callback = on_service_callback
        self._on_channel_callback = on_channel_callback

    async def send_to_service(self, service: str, dialog: Dict) -> None:
        raise NotImplementedError

    async def send_to_channel(self, channel_id: str, user_id: str, response: str) -> None:
        raise NotImplementedError


TAgentGateway = TypeVar('TAgentGateway', bound=AgentGatewayBase)


class ServiceGatewayConnectorBase:
    _service_config: dict
    _formatter: Callable

    def __init__(self, service_config: dict, formatter: Callable) -> None:
        self._service_config = service_config
        self._formatter = formatter

    async def send_to_service(self, dialogs: List[Dict]) -> List[Any]:
        raise NotImplementedError


TServiceGatewayConnectorBase = TypeVar('TServiceGatewayConnectorBase', bound=ServiceGatewayConnectorBase)


class ServiceGatewayBase:
    _to_service_callback: Callable

    def __init__(self, to_service_callback: Callable, *args, **kwargs) -> None:
        super(ServiceGatewayBase, self).__init__(*args, **kwargs)
        self._to_service_callback = to_service_callback


TServiceGateway = TypeVar('TServiceGateway', bound=ServiceGatewayBase)


class ChannelGatewayConnectorBase:
    _config: dict
    _channel_id: str
    _on_channel_callback: Callable

    def __init__(self, config: Dict, on_channel_callback: Callable) -> None:
        self._config = config
        self._channel_id = self._config['channel']['id']
        self._on_channel_callback = on_channel_callback

    async def send_to_channel(self, user_id: str, response: str) -> None:
        raise NotImplementedError


TChannelGatewayConnectorBase = TypeVar('TChannelGatewayConnectorBase', bound=ChannelGatewayConnectorBase)


class ChannelGatewayBase:
    _to_channel_callback: Callable

    def __init__(self, to_channel_callback: Callable, *args, **kwargs) -> None:
        super(ChannelGatewayBase, self).__init__(*args, **kwargs)
        self._to_channel_callback = to_channel_callback

    async def send_to_agent(self, utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        raise NotImplementedError


TChannelGateway = TypeVar('TChannelGateway', bound=ChannelGatewayBase)
