import asyncio
from collections import defaultdict
from typing import Dict, List

from agent_orange.core.transport.transport import TransportBus
from core.state_schema import Dialog


class Agent:
    _config: Dict
    _transport_bus: TransportBus
    _pipeline: List
    _pipeline_routing_map: Dict[frozenset, List[str]]
    _responding_service: str
    _dialogs: Dict[str, Dialog]
    _incoming_utterances: Dict[str, List[str]]
    _incoming_utterances_locks: Dict[str, List[asyncio.Lock]]

    def __init__(self, config: dict) -> None:
        pass
