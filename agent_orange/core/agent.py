import asyncio
from datetime import datetime
from collections import defaultdict, namedtuple
from typing import Dict, List, Union

from agent_orange.core.utils import run_sync_in_executor
from agent_orange.core.transport.transport import TransportBus
from core.state_manager import StateManager
from core.state_schema import Dialog


TIMEOUT_MESSAGE = 'Sorry, something went wrong and we are not able to process your request =('


DialogId = namedtuple('DialogId', ['channel', 'user_id'])
IncomingUtterance = namedtuple('IncomingUtterance', ['utterance', 'channel', 'user_id', 'reset_dialog'])


class Agent:
    _config: Dict
    _loop: asyncio.AbstractEventLoop
    _transport_bus: TransportBus
    _state_manager: StateManager
    _pipeline: List[Union[str, List[str]]]
    _pipeline_routing_map: Dict[frozenset, List[str]]
    _responding_service: str
    _response_timeout: float
    _dialogs: Dict[DialogId, Dialog]
    _utterances_queue: Dict[DialogId, List[IncomingUtterance]]
    _utterances_locks: Dict[DialogId, asyncio.Lock]
    _responses_events: Dict[DialogId, asyncio.Event]

    def __init__(self, config: dict) -> None:
        self._config = config
        self._loop = asyncio.get_event_loop()
        self._transport_bus = TransportBus(config=config, callback=self._on_service_message_callback)
        self._state_manager = StateManager()

        self._pipeline = config['agent']['pipeline']
        self._pipeline_routing_map = self._make_pipeline_routing_map(self._pipeline)
        self._responding_service = self._pipeline[-1]
        self._response_timeout = config['agent']['response_timeout_sec']

        self._dialogs = {}
        self._utterances_queue = defaultdict(list)
        self._utterances_locks = defaultdict(asyncio.Lock)
        self._responses_events = defaultdict(asyncio.Event)

    @staticmethod
    def _make_pipeline_routing_map(pipeline: List[Union[str, List[str]]]) -> Dict[frozenset, List[str]]:
        pipeline_routing_map = {}
        pipeline_routing_map[frozenset()] = list(pipeline[0])

        cumul_skills = []

        for i, skills in enumerate(pipeline[1:]):
            cumul_skills.extend(list(pipeline[i - 1]))
            pipeline_routing_map[frozenset(cumul_skills)] = list(skills)

        return pipeline_routing_map

    async def interact(self, utterance: str, channel: str, user_id: str, reset_dialog: bool) -> str:
        dialog_id = DialogId(channel=channel, user_id=user_id)
        inconing_utterance = IncomingUtterance(utterance=utterance, channel=channel,
                                               user_id=user_id, reset_dialog=reset_dialog)

        self._utterances_queue[dialog_id].append(inconing_utterance)

        async with self._utterances_locks[dialog_id]:
            response_event = self._responses_events[dialog_id]
            response_event.clear()
            await self._loop.create_task(self._process_next_utterance(dialog_id))
            await asyncio.wait_for(response_event.wait(), self._response_timeout)

            if not True:
                pass
            else:
                response = TIMEOUT_MESSAGE

            return response

    async def _process_next_utterance(self, dialog_id: DialogId) -> None:
        incoming_utterance = self._utterances_queue[dialog_id].pop(0)

        utterance = incoming_utterance.utterance
        channel = incoming_utterance.channel
        user_id = incoming_utterance.user_id
        reset_dialog = incoming_utterance.reset_dialog

        if dialog_id not in self._dialogs.keys():
            users = await run_sync_in_executor(self._state_manager.get_or_create_users,
                                               user_telegram_ids=[user_id],
                                               user_device_types=[None])

            dialogs = await run_sync_in_executor(self._state_manager.get_or_create_dialogs,
                                                 users=[users[0]],
                                                 locations=[None],
                                                 channel_types=[channel],
                                                 should_reset=[reset_dialog])

            dialog = dialogs[0]
            self._dialogs[dialog_id] = dialog

            await run_sync_in_executor(self._state_manager.add_human_utterances,
                                       dialogs=[dialog],
                                       texts=[utterance],
                                       date_times=[datetime.utcnow()])


    async def _on_service_message_callback(self, payload: dict) -> None:
        pass
