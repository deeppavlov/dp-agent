import asyncio
from itertools import chain
from logging import getLogger
from datetime import datetime
from collections import defaultdict, namedtuple
from typing import Dict, List, Union, Callable, Awaitable

from mongoengine import connection, connect

from core.state.model import Bot, Dialog, Human, HumanUtterance, BotUtterance


TIMEOUT_MESSAGE = 'Sorry, we could not answer your request'
PIPELINE_ORDER = ['utterance_annotators', 'skill_selector', 'skills', 'response_selector',
                  'response_annotators', 'response_formatter']

logger = getLogger(__name__)

ChannelUserKey = namedtuple('ChannelUserKey', ['channel_id', 'user_id'])
IncomingUtterance = namedtuple('IncomingUtterance', ['utterance', 'reset_dialog'])


def connect_mongo(config: dict) -> connection:
    db_host = config['database']['host']
    db_port = config['database']['port']
    db_name = f'{config["agent_namespace"]}_{config["agent"]["name"]}'

    return connect(host=db_host, port=db_port, db=db_name)


class Agent:
    _config: Dict
    _loop: asyncio.AbstractEventLoop
    _connection: connection
    _bot: Bot

    _pipeline: Dict[str, List[str]]
    _actual_stages = List[str]

    _to_service_callback: Callable[[str, Dict], Awaitable]
    _to_channel_callback: Callable[[str, str, str], Awaitable]

    _response_timeout: float
    _dialogs: Dict[ChannelUserKey, Dialog]
    _dialogs_stages: Dict[ChannelUserKey, int]
    _pruned_services: Dict[ChannelUserKey, List[str]]
    _dialog_uuid_key_map: Dict[str, ChannelUserKey]
    _utterances_queue: Dict[ChannelUserKey, List[IncomingUtterance]]
    _utterances_locks: Dict[ChannelUserKey, asyncio.Lock]
    _responses_events: Dict[ChannelUserKey, asyncio.Event]
    _dialog_locks: Dict[ChannelUserKey, asyncio.Lock]

    def __init__(self, config: dict,
                 to_service_callback: Callable[[str, Dict], Awaitable],
                 to_channel_callback: Callable[[str, str, str], Awaitable]) -> None:

        self._config = config
        self._loop = asyncio.get_event_loop()
        self._connection = connect_mongo(config)
        self._bot = self._loop.run_until_complete(Bot.get_or_create())

        self._pipeline = config['agent']['pipeline']
        self._actual_stages = [stage for stage in PIPELINE_ORDER if self._pipeline[stage]]
        logger.info(f'Initiated pipeline: {str([self._pipeline[stage] for stage in self._actual_stages])}')

        self._to_service_callback = to_service_callback
        self._to_channel_callback = to_channel_callback

        self._response_timeout = config['agent']['response_timeout_sec']
        self._dialogs = {}
        self._dialogs_stages = {}
        self._pruned_services = defaultdict(list)
        self._dialog_uuid_key_map = {}
        self._utterances_queue = defaultdict(list)
        self._utterances_locks = defaultdict(asyncio.Lock)
        self._responses_events = defaultdict(asyncio.Event)
        self._dialog_locks = defaultdict(asyncio.Lock)

        logger.info(f'Agent {self._config["agent"]["name"]} initiated')

    async def on_service_message(self, partial_dialog_state: dict) -> None:
        dialog_uuid = partial_dialog_state['uuid']
        logger.debug(f'Received from service partial state for dialog: {dialog_uuid}')
        channel_user_key = self._dialog_uuid_key_map.get(dialog_uuid, None)

        if channel_user_key:
            async with self._dialog_locks[channel_user_key]:
                await self._add_service_responses(channel_user_key, partial_dialog_state)
                await self._route_to_next_services(channel_user_key)
        else:
            logger.warning(f'Dialog uuid {dialog_uuid} was not found in _dialog_uuid_key_map')

    async def _add_service_responses(self, channel_user_key: ChannelUserKey, partial_dialog_state: dict) -> None:
        last_received_utterance = partial_dialog_state['utterances'][0]
        utterance_uuid: str = last_received_utterance['uuid']
        service_responses: dict = last_received_utterance['service_responses']
        dialog = self._dialogs[channel_user_key]

        for utterance in reversed(dialog.utterances):
            if str(utterance.uuid) == utterance_uuid:
                for service_name, service_response in service_responses.items():
                    utterance.add_service_response(service_name, service_response)
                logger.debug(f'Added to dialog {dialog.uuid} responses from partial state: {str(partial_dialog_state)}')
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

            await self._loop.create_task(self._to_channel_callback(channel_id=channel_id,
                                                                   user_id=user_id,
                                                                   response=response))

            await dialog.save()

    async def _process_next_utterance(self, channel_user_key: ChannelUserKey) -> None:
        incoming_utterance = self._utterances_queue[channel_user_key].pop(0)
        utterance = incoming_utterance.utterance
        reset_dialog = incoming_utterance.reset_dialog
        channel_type = channel_user_key.channel_id

        user = await Human.get_or_create(user_telegram_id=channel_user_key.user_id, device_type=None)
        dialog = self._dialogs.get(channel_user_key, None)

        if reset_dialog:
            if dialog:
                await dialog.save()
                dialog_uuid = str(dialog.uuid)

                if self._dialog_uuid_key_map.pop(dialog_uuid, None):
                    logger.debug(f'Dialog uuid {dialog_uuid} was removed from _dialog_uuid_key_map')
                else:
                    logger.warning(f'Dialog uuid {dialog_uuid} was not found in _dialog_uuid_key_map')

            dialog = Dialog(user=user, bot=self._bot, channel_type=channel_type, location=None)
            self._dialog_uuid_key_map[dialog.uuid] = channel_user_key
            self._dialogs[channel_user_key] = dialog
            logger.debug(f'Created dialog uuid: {dialog.uuid} key: {str(channel_user_key)}')

        if not dialog:
            dialog: Dialog = Dialog.get_or_create(user=user, bot=self._bot, channel_type=channel_type, location=None)
            self._dialog_uuid_key_map[dialog.uuid] = channel_user_key
            self._dialogs[channel_user_key] = dialog
            logger.debug(f'Added dialog uuid: {dialog.uuid} key: {str(channel_user_key)}')

        human_utterance = await HumanUtterance.get_or_create(text=utterance, user=user, date_time=datetime.utcnow())
        dialog.add_utterance(human_utterance)
        logger.debug(f'Added human utterance: {utterance} utt_uuid: {human_utterance.uuid} to dialog: {dialog.uuid}')

        await self._loop.create_task(self._route_to_next_services(channel_user_key))

    async def _route_to_next_services(self, channel_user_key: ChannelUserKey) -> None:
        dialog = self._dialogs[channel_user_key]
        dialog_uuid = dialog.uuid
        logger.debug(f'Routing to next service dialog: {dialog_uuid}')

        if channel_user_key not in self._dialogs_stages.keys():
            logger.debug(f'Beginning going through the pipeline for dialog {dialog_uuid}')
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
            await self._loop.create_task(self._to_service_callback(service_name=service, dialog_state=dialog_state))
            logger.debug(f'Dialog {dialog.uuid} state was sent to services: {str(services)}')

    async def _process_pipeline_stage(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        if pipeline_stage in ['utterance_annotators', 'response_annotators']:
            await self._on_annotators(channel_user_key, pipeline_stage)
        elif pipeline_stage == 'skill_selector':
            await self._on_skill_selector(channel_user_key, pipeline_stage)
        elif pipeline_stage == 'skills':
            await self._on_skills(channel_user_key, pipeline_stage)
        elif pipeline_stage == 'response_selector':
            await self._on_response_selector(channel_user_key, pipeline_stage)
        elif pipeline_stage == 'response_formatter':
            await self._on_response_formatter(channel_user_key, pipeline_stage)

    async def _on_annotators(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: Union[HumanUtterance, BotUtterance] = dialog.utterances[-1]
        stage_services = self._pipeline[pipeline_stage]

        for service in stage_services:
            annotation = last_utterance.pop_service_response(service_name=service)
            if annotation:
                last_utterance.add_annotation(service_name=service, annotation=annotation)
                logger.debug(f'Added annotation for utterance {last_utterance.uuid} in dialog {dialog.uuid}')

    async def _on_skill_selector(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: HumanUtterance = dialog.utterances[-1]
        stage_services = self._pipeline[pipeline_stage]
        selector_service = stage_services[0]
        selector_response = last_utterance.pop_service_response(service_name=selector_service)

        if selector_response:
            skills = self._pipeline['skills']
            response_skills = selector_response['skill_names'] if selector_response else []
            selected_skills = set(skills).intersection(set(response_skills))
            pruned_skills = list(set(skills) - selected_skills) if selected_skills else []
            self._pruned_services[channel_user_key].extend(pruned_skills)
            logger.debug(f'Pruned services {str(self._pruned_services[channel_user_key])} in dialog {dialog.uuid}')

    async def _on_skills(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: HumanUtterance = dialog.utterances[-1]
        stage_services = self._pipeline[pipeline_stage]
        selected_skills = []

        for service in stage_services:
            skill_response = last_utterance.pop_service_response(service_name=service)
            if skill_response:
                last_utterance.add_skill_response(skill_response=skill_response)
                logger.debug(f'Added skill response for utterance {last_utterance.uuid} in dialog {dialog.uuid}')

        # adding BotUtterance if skill selector is not defined
        if not self._pipeline['response_selector'] and selected_skills:
            response: dict = selected_skills[0]
            response_skill = response['name']
            response_text = response['text']
            response_confidence = response['confidence']

            bot_utterance = BotUtterance(user=self._bot,
                                         date_time=datetime.utcnow(),
                                         orig_text=response_text,
                                         active_skill=response_skill,
                                         confidence=response_confidence)

            dialog.add_utterance(bot_utterance)
            logger.debug(f'Added bot utterance {bot_utterance.uuid} to dialog {dialog.uuid} from random skill')

    async def _on_response_selector(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: HumanUtterance = dialog.utterances[-1]
        stage_services = self._pipeline[pipeline_stage]

        selector_service = stage_services[0]
        selector_response = last_utterance.pop_service_response(service_name=selector_service)

        if selector_response:
            response_skill = selector_response['name']
            response_text = selector_response['text']
            response_confidence = selector_response['confidence']

            bot_utterance = BotUtterance(user=self._bot,
                                         date_time=datetime.utcnow(),
                                         orig_text=response_text,
                                         active_skill=response_skill,
                                         confidence=response_confidence)

            dialog.add_utterance(bot_utterance)
            logger.debug(f'Added bot utterance {bot_utterance.uuid} to dialog {dialog.uuid}')

    async def _on_response_formatter(self, channel_user_key: ChannelUserKey, pipeline_stage: str) -> None:
        dialog = self._dialogs[channel_user_key]
        last_utterance: BotUtterance = dialog.utterances[-1]
        stage_services = self._pipeline[pipeline_stage]

        formatter_service = stage_services[0]
        formatter_response = last_utterance.pop_service_response(formatter_service)

        if formatter_response:
            last_utterance.set_text(formatter_response['formatted_text'])
            logger.debug(f'Added formatted response to bot utterance {last_utterance.uuid} to dialog {dialog.uuid}')
