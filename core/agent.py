import asyncio
from itertools import chain
from logging import getLogger
from datetime import datetime
from collections import defaultdict, namedtuple
from typing import Dict, List, Union, Awaitable

from core.utils import run_sync_in_executor
from core.state.manager import StateManager
from core.state.schema import Dialog, HumanUtterance, BotUtterance


TIMEOUT_MESSAGE = 'Sorry, we could not answer your request'
PIPELINE_ORDER = ['utterance_annotators', 'skill_selector', 'skills', 'response_selector',
                  'response_annotators', 'response_formatter']

logger = getLogger(__name__)

ChannelUserKey = namedtuple('ChannelUserKey', ['channel_id', 'user_id'])
IncomingUtterance = namedtuple('IncomingUtterance', ['utterance', 'reset_dialog'])


class Agent:
    _config: Dict
    _loop: asyncio.AbstractEventLoop
    _state_manager: StateManager
    _pipeline: Dict[str, List[str]]
    _actual_stages = List[str]

    _to_service_callback: Awaitable
    _to_channel_callback: Awaitable

    _response_timeout: float
    _dialogs: Dict[ChannelUserKey, Dialog]
    _dialogs_stages: Dict[ChannelUserKey, int]
    _pruned_services: Dict[ChannelUserKey, List[str]]
    _dialog_id_key_map: Dict[str, ChannelUserKey]
    _utterances_queue: Dict[ChannelUserKey, List[IncomingUtterance]]
    _utterances_locks: Dict[ChannelUserKey, asyncio.Lock]
    _responses_events: Dict[ChannelUserKey, asyncio.Event]
    _dialog_locks: Dict[ChannelUserKey, asyncio.Lock]

    def __init__(self, config: dict, to_service_callback: Awaitable, to_channel_callback: Awaitable) -> None:
        self._config = config
        self._loop = asyncio.get_event_loop()
        self._state_manager = StateManager(config)

        self._pipeline = config['agent']['pipeline']
        self._actual_stages = [stage for stage in PIPELINE_ORDER if self._pipeline[stage]]
        logger.info(f'Initiated pipeline: {str([self._pipeline[stage] for stage in self._actual_stages])}')

        self._to_service_callback = to_service_callback
        self._to_channel_callback = to_channel_callback

        self._response_timeout = config['agent']['response_timeout_sec']
        self._dialogs = {}
        self._dialogs_stages = {}
        self._pruned_services = defaultdict(list)
        self._dialog_id_key_map = {}
        self._utterances_queue = defaultdict(list)
        self._utterances_locks = defaultdict(asyncio.Lock)
        self._responses_events = defaultdict(asyncio.Event)
        self._dialog_locks = defaultdict(asyncio.Lock)

        logger.info(f'Agent {self._config["agent"]["name"]} initiated')

    async def on_service_message(self, partial_dialog_state: dict) -> None:
        dialog_id = partial_dialog_state['id']
        logger.debug(f'Received from service partial state for dialog: {dialog_id}')
        channel_user_key = self._dialog_id_key_map.get(dialog_id, None)

        if channel_user_key:
            async with self._dialog_locks[channel_user_key]:
                await self._add_service_responses(channel_user_key, partial_dialog_state)
                await self._route_to_next_services(channel_user_key)

    async def _add_service_responses(self, channel_user_key: ChannelUserKey, partial_dialog_state: dict) -> None:
        last_received_utterance = partial_dialog_state['utterances'][0]
        utterance_id: str = last_received_utterance['id']
        service_responses: dict = last_received_utterance['service_responses']
        dialog = self._dialogs[channel_user_key]

        for utterance in reversed(dialog.utterances):
            if str(utterance.id) == utterance_id:
                current_responses = dict(**utterance.service_responses)
                current_responses.update(service_responses)
                utterance.service_responses = current_responses
                utterance.save()
                logger.debug(f'Added to dialog {dialog.id} responses from partial state: {str(partial_dialog_state)}')
                break

    async def on_channel_message(self, utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        channel_user_key = ChannelUserKey(channel_id=channel_id, user_id=user_id)
        incoming_utterance = IncomingUtterance(utterance=utterance, reset_dialog=reset_dialog)
        self._utterances_queue[channel_user_key].append(incoming_utterance)
        logger.debug(f'Received utt: {utterance}, usr: {user_id}, chnl: {channel_id}')

        async with self._utterances_locks[channel_user_key]:
            logger.debug(f'Processing utt: {utterance}, usr: {user_id}, chnl: {channel_id}')
            response_event = self._responses_events[channel_user_key]
            response_event.clear()

            await self._loop.create_task(self._process_next_utterance(channel_user_key))

            try:
                await asyncio.wait_for(response_event.wait(), self._response_timeout)
            except asyncio.TimeoutError:
                pass

            self._dialogs_stages.pop(channel_user_key, None)
            self._pruned_services.pop(channel_user_key, None)

            dialog = self._dialogs[channel_user_key]
            last_utterance: Union[BotUtterance, HumanUtterance] = dialog.utterances[-1]
            response = last_utterance.text if isinstance(last_utterance, BotUtterance) else TIMEOUT_MESSAGE
            logger.debug(f'Sent response resp: {response}, usr: {user_id}, chnl: {channel_id}')

            await self._to_channel_callback(channel_id=channel_id, user_id=user_id, message=response)

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
            logger.debug(f'Created dialog id: {dialog.id} key: {str(channel_user_key)}')

        await run_sync_in_executor(self._state_manager.add_human_utterances,
                                   dialogs=[dialog],
                                   texts=[utterance],
                                   date_times=[datetime.utcnow()])

        human_utt: HumanUtterance = dialog.utterances[-1]
        logger.debug(f'Added human utterance: {utterance} utt_id: {human_utt.id} to dialog: {dialog.id}')

        await self._loop.create_task(self._route_to_next_services(channel_user_key))

    async def _route_to_next_services(self, channel_user_key: ChannelUserKey) -> None:
        dialog = self._dialogs[channel_user_key]
        logger.debug(f'Routing to next service dialog: {dialog.id}')

        if channel_user_key not in self._dialogs_stages.keys():
            logger.debug(f'Beginning going through the pipeline for dialog {dialog.id}')
            self._dialogs_stages[channel_user_key] = 0
            first_stage_name = self._actual_stages[0]
            services = self._pipeline[first_stage_name]
            await self._send_to_services(channel_user_key, services)
            return

        stage_index = self._dialogs_stages[channel_user_key]
        current_stage_name = self._actual_stages[stage_index]
        current_stage_services = self._pipeline[current_stage_name]

        last_utterance: Union[BotUtterance, HumanUtterance] = dialog.utterances[-1]
        responded_services = list(last_utterance.service_responses.keys())
        logger.debug(f'On stage {stage_index}, {current_stage_name}, responded services: {str(responded_services)}')
        pruned_services = self._pruned_services[channel_user_key]

        if set(current_stage_services).issubset(set(chain(responded_services, pruned_services))):
            await self._process_pipeline_stage(channel_user_key, current_stage_name)
            stage_index += 1

            if stage_index + 1 > len(self._actual_stages):
                self._responses_events[channel_user_key].set()
            else:
                self._dialogs_stages[channel_user_key] = stage_index
                next_stage_name = self._actual_stages[stage_index]
                next_stage_services = self._pipeline[next_stage_name]
                selected_services = list(set(next_stage_services) - set(pruned_services))
                await self._send_to_services(channel_user_key, selected_services)

    async def _send_to_services(self, channel_user_key: ChannelUserKey, services: List[str]) -> None:
        dialog = self._dialogs[channel_user_key]
        dialog_state = dialog.to_dict()

        for service in services:
            await self._loop.create_task(self._to_service_callback(service=service, dialog_state=dialog_state))
            logger.debug(f'Dialog {dialog.id} state was sent to services: {str(services)}')

    async def _process_pipeline_stage(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: Union[HumanUtterance, BotUtterance] = dialog.utterances[-1]
        service_responses = dict(**last_utterance.service_responses)
        stage_services = self._pipeline[pipeline_stage]

        if pipeline_stage in ['utterance_annotators', 'response_annotators']:
            await self._on_annotators(last_utterance, service_responses, stage_services)
            logger.debug(f'Updated annotations for utterance {last_utterance.id} in dialog {dialog.id}')
        elif pipeline_stage == 'skill_selector':
            await self._on_skill_selector(service_responses, stage_services, channel_user_key)
            logger.debug(f'Pruned services {str(self._pruned_services[channel_user_key])} in dialog {dialog.id}')
        elif pipeline_stage == 'skills':
            await self._on_skills(dialog, last_utterance, service_responses, stage_services)
            logger.debug(f'Updated selected skills for utterance {last_utterance.id} in dialog {dialog.id}')

    async def _on_annotators(self, last_utterance: Union[HumanUtterance, BotUtterance], service_responses: dict,
                             stage_services: List[str]) -> None:

        annotations = dict(**last_utterance.annotations)

        for service in stage_services:
            annotation = service_responses.pop(service, None)
            if annotation:
                annotations[service] = annotation

        last_utterance.annotations = annotations
        last_utterance.service_responses = service_responses
        last_utterance.save()

    async def _on_skill_selector(self, service_responses: dict, stage_services: List[str],
                                 channel_user_key: ChannelUserKey) -> None:

        selector_service = stage_services[0]
        skills = self._pipeline['skills']
        selector_response = service_responses.pop(selector_service, None)
        response_skills = selector_response['skill_names'] if selector_response else []
        selected_skills = set(skills).intersection(set(response_skills))
        pruned_skills = list(set(skills) - selected_skills) if selected_skills else []
        self._pruned_services[channel_user_key].extend(pruned_skills)

    async def _on_skills(self, dialog: Dialog, last_utterance: HumanUtterance, service_responses: dict,
                         stage_services: List[str]) -> None:

        selected_skills = []

        for service in stage_services:
            skill_response = service_responses.pop(service, None)
            if skill_response:
                selected_skills.append(skill_response)

        last_utterance.selected_skills = selected_skills
        last_utterance.service_responses = service_responses
        last_utterance.save()

        # adding BotUtterance if skill selector is not defined
        if not self._pipeline['response_selector'] and selected_skills:
            response: dict = selected_skills[0]
            response_skill = response['name']
            response_text = response['text']
            response_confidence = response['confidence']

            await run_sync_in_executor(self._state_manager.add_bot_utterances,
                                       dialogs=[dialog],
                                       orig_texts=[response_text],
                                       texts=[response_text],
                                       date_times=[datetime.utcnow()],
                                       active_skills=[response_skill],
                                       confidences=[response_confidence])

            bot_utterance: BotUtterance = dialog.utterances[-1]
            logger.debug(f'Added bot utterance {bot_utterance.id} to dialog {dialog.id} from random skill')
