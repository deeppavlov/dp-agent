from abc import ABCMeta, abstractmethod

from core.transport.gateway import AbstractTransportConnector
from core.transport.transport_map import get_transport_connector


class AbstractServiceConnector(metaclass=ABCMeta):
    transport_connector: AbstractTransportConnector

    pass
