import asyncio
from collections import defaultdict
from typing import Dict, List, Union

from agent_orange.core.transport.transport import TransportBus
from core.state_schema import Dialog


class Agent:
    _config: Dict
    _transport_bus: TransportBus
    _pipeline: List[Union[str, List[str]]]
    _pipeline_routing_map: Dict[frozenset, List[str]]
    _responding_service: str
    _dialogs: Dict[str, Dialog]
    _incoming_utterances: Dict[str, List[str]]
    _incoming_utterances_locks: Dict[str, asyncio.Lock]

    def __init__(self, config: dict) -> None:
        self._config = config
        self._transport_bus = TransportBus(config=config, callback=self._on_service_message_callback())

        self._pipeline = config['agent']['pipeline']
        self._pipeline_routing_map = self._make_pipeline_routing_map(self._pipeline)
        self._responding_service = self._pipeline[-1]

        self._dialogs = {}
        self._incoming_utterances = {}
        self._incoming_utterances_locks = defaultdict(asyncio.Lock)

    @staticmethod
    def _make_pipeline_routing_map(pipeline: List[Union[str, List[str]]]) -> Dict[frozenset, List[str]]:
        pipeline_routing_map = {}
        pipeline_routing_map[frozenset()] = list(pipeline[0])

        cumul_skills = []

        for i, skills in enumerate(pipeline[1:]):
            cumul_skills.extend(list(pipeline[i - 1]))
            pipeline_routing_map[frozenset(cumul_skills)] = list(skills)

        return pipeline_routing_map

    async def _on_service_message_callback(self, payload: dict) -> None:
        pass
