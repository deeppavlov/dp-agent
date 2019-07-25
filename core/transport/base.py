from abc import ABCMeta, abstractmethod


class AbstractTransportGateway(metaclass=ABCMeta):
    _config: dict  # for now it is dummy, using z_dev_transport_config.py

    def __init__(self, config: dict) -> None:
        self._config = config

    @abstractmethod
    async def process(self, service: str, dialog_state: dict) -> dict:
        pass


class AbstractTransportConnector(metaclass=ABCMeta):
    pass


class AbstractComponentConnector(metaclass=ABCMeta):
    _transport_connector: AbstractTransportConnector
    pass
