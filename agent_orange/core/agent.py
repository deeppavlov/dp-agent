import asyncio
from logging import getLogger
from datetime import datetime
from collections import defaultdict, namedtuple
from typing import Dict, List, Union

from agent_orange.core.utils import run_sync_in_executor
from agent_orange.core.transport.transport import TransportBus
from core.state_manager import StateManager
from core.state_schema import Dialog, HumanUtterance


TIMEOUT_MESSAGE = 'Sorry, we could not answer your request'
END_OF_PIPELINE_MARKER = '#end'

logger = getLogger(__name__)

ChannelUserKey = namedtuple('ChannelUserKey', ['channel_id', 'user_id'])
IncomingUtterance = namedtuple('IncomingUtterance', ['utterance', 'reset_dialog'])


class Agent:
    _config: Dict
    _loop: asyncio.AbstractEventLoop
    _transport_bus: TransportBus
    _state_manager: StateManager
    _pipeline: List[Union[str, List[str]]]
    _pipeline_routing_map: Dict[frozenset, List[str]]
    _responding_service: str
    _response_timeout: float
    _dialogs: Dict[ChannelUserKey, Dialog]
    _dialog_id_key_map: Dict[str, ChannelUserKey]
    _utterances_queue: Dict[ChannelUserKey, List[IncomingUtterance]]
    _utterances_locks: Dict[ChannelUserKey, asyncio.Lock]
    _responses_events: Dict[ChannelUserKey, asyncio.Event]
    _annotations_locks: Dict[ChannelUserKey, asyncio.Lock]

    def __init__(self, config: dict) -> None:
        self._config = config
        self._loop = asyncio.get_event_loop()
        self._transport_bus = TransportBus(config=config, callback=self.on_service_message_callback)
        self._state_manager = StateManager()

        self._pipeline = config['agent']['pipeline']
        self._pipeline_routing_map = self._make_pipeline_routing_map(self._pipeline)
        self._responding_service = self._pipeline[-1][0]
        self._response_timeout = config['agent']['response_timeout_sec']

        self._dialogs = {}
        self._dialog_id_key_map = {}
        self._utterances_queue = defaultdict(list)
        self._utterances_locks = defaultdict(asyncio.Lock)
        self._responses_events = defaultdict(asyncio.Event)
        self._annotations_locks = defaultdict(asyncio.Lock)

        logger.info(f'Agent {self._config["agent"]["name"]} initiated')

    @staticmethod
    def _make_pipeline_routing_map(pipeline: List[Union[str, List[str]]]) -> Dict[frozenset, List[str]]:
        pipeline_routing_map = {}
        pipeline_routing_map[frozenset()] = pipeline[0]
        cumul_skills = []

        for i, skills in enumerate(pipeline[1:]):
            cumul_skills.extend(pipeline[i])
            pipeline_routing_map[frozenset(cumul_skills)] = list(skills)

        cumul_skills.extend(list(pipeline[-1]))
        pipeline_routing_map[frozenset(cumul_skills)] = [END_OF_PIPELINE_MARKER]

        routing_map_str = '\n'.join([f'\t{str(key)}: {str(value)}' for key, value in pipeline_routing_map.items()])
        logger.debug(f'Initiated pipeline routing map:\n{routing_map_str}')

        return pipeline_routing_map

    async def interact(self, utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> str:
        channel_user_key = ChannelUserKey(channel_id=channel_id, user_id=user_id)
        incoming_utterance = IncomingUtterance(utterance=utterance, reset_dialog=reset_dialog)
        self._utterances_queue[channel_user_key].append(incoming_utterance)
        logger.debug(f'Received utt: [{utterance}], usr: [{user_id}], chnl: [{channel_id}]')

        async with self._utterances_locks[channel_user_key]:
            logger.debug(f'Processing utt: [{utterance}], usr: [{user_id}], chnl: [{channel_id}]')
            response_event = self._responses_events[channel_user_key]
            response_event.clear()

            await self._loop.create_task(self._process_next_utterance(channel_user_key))
            await asyncio.wait_for(response_event.wait(), self._response_timeout)

            dialog = self._dialogs[channel_user_key]
            last_dialog_utt: HumanUtterance = dialog.utterances[-1]
            response = last_dialog_utt.to_dict().get(self._responding_service, None) or TIMEOUT_MESSAGE

            await run_sync_in_executor(self._state_manager.add_bot_utterances,
                                       dialogs=[dialog],
                                       orig_texts=[response],
                                       texts=[response],
                                       date_times=[datetime.utcnow()],
                                       active_skills=[self._responding_service],
                                       confidences=[1])

            logger.debug(f'Added bot response: [{response}] to dialog: [{dialog.id}]')

            return response

    async def _process_next_utterance(self, channel_user_key: ChannelUserKey) -> None:
        incoming_utterance = self._utterances_queue[channel_user_key].pop(0)
        utterance = incoming_utterance.utterance
        reset_dialog = incoming_utterance.reset_dialog
        dialog = self._dialogs.get(channel_user_key, None)

        if reset_dialog or not dialog:
            users = await run_sync_in_executor(self._state_manager.get_or_create_users,
                                               user_telegram_ids=[channel_user_key.user_id],
                                               user_device_types=[None])

            dialogs = await run_sync_in_executor(self._state_manager.get_or_create_dialogs,
                                                 users=[users[0]],
                                                 locations=[None],
                                                 channel_types=[channel_user_key.channel_id],
                                                 should_reset=[reset_dialog])

            if dialog:
                dialog.save()
                self._dialog_id_key_map.pop(str(dialog.id), None)

            dialog = dialogs[0]
            self._dialogs[channel_user_key] = dialogs[0]
            self._dialog_id_key_map[str(dialog.id)] = channel_user_key
            logger.debug(f'Created dialog id: [{dialog.id}] key: [{str(channel_user_key)}]')

        utterances = await run_sync_in_executor(self._state_manager.add_human_utterances,
                                                dialogs=[dialog],
                                                texts=[utterance],
                                                date_times=[datetime.utcnow()])

        human_utt: HumanUtterance = utterances[0]
        logger.debug(f'Added human utterance: [{utterance}] utt_id: {human_utt.id} to dialog: [{dialog.id}]')

        await self._loop.create_task(self._route_to_next_service(channel_user_key))

    async def _route_to_next_service(self, channel_user_key: ChannelUserKey) -> None:
        dialog = self._dialogs[channel_user_key]
        logger.debug(f'Routing to next service dialog: [{dialog.id}]')
        last_utterance: HumanUtterance = dialog.utterances[-1]
        annotations: dict = last_utterance.to_dict()['annotations']
        responded_services_set = frozenset(annotations.keys())
        next_services = self._pipeline_routing_map.get(responded_services_set, None)

        if next_services:
            if END_OF_PIPELINE_MARKER in next_services:
                self._responses_events[channel_user_key].set()
                logger.debug(f'Finished pipeline for dialog: [{dialog.id}]')
            else:
                dialog_state = dialog.to_dict()

                for service in next_services:
                    await self._loop.create_task(self._transport_bus.process(service, dialog_state))

                service_names_str = ' '.join(next_services)
                logger.debug(f'State of dialog: [{dialog.id}] processed to services: [{service_names_str}]')

    async def _update_annotations(self, channel_user_key: ChannelUserKey, partial_dialog_state: dict) -> None:
        dialog = self._dialogs[channel_user_key]
        annotated_utterance = partial_dialog_state['utterances'][0]
        utterance_id: str = annotated_utterance['id']
        annotations: dict = annotated_utterance['annotations']

        # this is clumsy, but 'reversed' makes it rather effective for prototype
        for utterance in reversed(dialog.utterances):
            if str(utterance.id) == utterance_id:
                utterance.annotations.update(annotations)
                logger.debug(f'Utterance: [{utterance_id}] updated with annotations: [{str(annotations)}]')
                break

    async def on_service_message_callback(self, partial_dialog_state: dict) -> None:
        dialog_id = partial_dialog_state['id']
        logger.debug(f'Received from service partial state for dialog: [{dialog_id}]')
        channel_user_key = self._dialog_id_key_map[dialog_id]

        async with self._annotations_locks[channel_user_key]:
            await self._update_annotations(channel_user_key, partial_dialog_state)
            await self._route_to_next_service(channel_user_key)
