from datetime import datetime
from typing import Sequence, Hashable, Any, Callable, List, Dict
from itertools import compress
import operator

from core.state_manager import StateManager
from core.skill_manager import SkillManager
from models.hardcode_utterances import TG_START_UTT
from core.state_schema import Dialog, Human

Profile = Dict[str, Any]


class Agent:
    def __init__(self, state_manager: StateManager, preprocessor: Callable,
                 postprocessor: Callable,
                 skill_manager: SkillManager) -> None:
        self.state_manager = state_manager
        self.preprocessor = preprocessor
        self.postprocessor = postprocessor
        self.skill_manager = skill_manager

    def __call__(self, utterances: Sequence[str], user_telegram_ids: Sequence[Hashable],
                 user_device_types: Sequence[Any],
                 date_times: Sequence[datetime], locations=Sequence[Any],
                 channel_types=Sequence[str]):
        should_reset = [utterance == TG_START_UTT for utterance in utterances]
        # here and further me stands for mongoengine
        me_users = self.state_manager.get_or_create_users(user_telegram_ids, user_device_types)
        me_dialogs = self.state_manager.get_or_create_dialogs(me_users, locations, channel_types,
                                                              should_reset)
        self.state_manager.add_human_utterances(me_dialogs, utterances, date_times)
        
        informative_dialogs = list(compress(me_dialogs, map(operator.not_, should_reset)))

        self._update_annotations(informative_dialogs)

        selected_skills = self.skill_manager.get_skill_responses(me_dialogs)
        self._update_utterances(me_dialogs, selected_skills, key='selected_skills')

        skill_names, responses, confidences, profiles = self.skill_manager(me_dialogs)
        self._update_profiles(me_users, profiles)

        self.state_manager.add_bot_utterances(me_dialogs, responses, responses,
                                              [datetime.utcnow()] * len(me_dialogs),
                                              skill_names, confidences)

        sent_responses = self.postprocessor(me_dialogs)
        self._update_utterances(me_dialogs, sent_responses, key='text')
        self._update_annotations(me_dialogs)

        return sent_responses  # return text only to the users

    def _update_annotations(self, me_dialogs: Sequence[Dialog]) -> None:
        annotations = self.preprocessor([i.to_dict() for i in me_dialogs])
        utterances = [dialog.utterances[-1] for dialog in me_dialogs]
        self.state_manager.add_annotations(utterances, annotations)

    def _update_profiles(self, me_users: Sequence[Human], profiles: List[Profile]) -> None:
        for me_user, profile in zip(me_users, profiles):
            if any(profile.values()):
                self.state_manager.update_user_profile(me_user, profile)

    def _update_utterances(self, me_dialogs: Sequence[Dialog], values: Sequence[Any],
                           key: str) -> None:
        if values:
            utterances = [dialog.utterances[-1] for dialog in me_dialogs]
            for utt, val in zip(utterances, values):
                self.state_manager.update_me_object(utt, {key: val})
