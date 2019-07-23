from abc import ABCMeta, abstractmethod


class AbstractTransportGateway(metaclass=ABCMeta):
    _config: dict

    def __init__(self, config: dict) -> None:
        self._config = config

    @abstractmethod
    def process(self, service: str, dialog_state: dict) -> dict:
        pass


class AbstractTransportConnector(metaclass=ABCMeta):
    pass
