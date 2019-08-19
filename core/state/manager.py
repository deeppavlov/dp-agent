from datetime import datetime
from typing import Sequence, Hashable, Any, Optional, Dict

from mongoengine import connect

from core.state.schema import Human, Bot, Utterance, HumanUtterance, BotUtterance, Dialog
from core import VERSION


BOT_ID = '5c7cf00e5c70e839bf9cb115'


def get_state(dialogs: Sequence[Dialog]):
    state = {'version': VERSION, 'dialogs': []}
    for d in dialogs:
        state['dialogs'].append(d.to_dict())
    return state


class StateManager:
    def __init__(self, config: dict):
        db_host = config['database']['host']
        db_port = config['database']['port']
        db_name = f'{config["agent_namespace"]}_{config["agent"]["name"]}'

        self._connection = connect(host=db_host, port=db_port, db=db_name)

        try:
            self._bot = Bot.objects(id__exact=BOT_ID)[0]
        except IndexError:
            self._bot = Bot(id=BOT_ID)
            self._bot.save()

    def get_or_create_users(self, user_telegram_ids=Sequence[Hashable], user_device_types=Sequence[Any]):
        users = []
        for user_telegram_id, device_type in zip(user_telegram_ids, user_device_types):
            user_query = Human.objects(user_telegram_id__exact=user_telegram_id)
            if not user_query:
                user = self.create_new_human(user_telegram_id, device_type)
            else:
                user = user_query[0]
            users.append(user)
        return users

    def get_or_create_dialogs(self, users, locations, channel_types, should_reset):
        dialogs = []
        for user, loc, channel_type, reset in zip(users, locations, channel_types, should_reset):
            if reset:
                dialog = self.create_new_dialog(user=user,
                                                bot=self._bot,
                                                location=loc,
                                                channel_type=channel_type)
            else:
                exist_dialogs = Dialog.objects(user__exact=user)
                if not exist_dialogs:
                    # TODO remove this "if" condition: it should never happen in production, only while testing
                    # TODO better to keep it:
                    dialog = self.create_new_dialog(user=user,
                                                    bot=self._bot,
                                                    location=loc,
                                                    channel_type=channel_type)
                else:
                    dialog = exist_dialogs[0]

            dialogs.append(dialog)
        return dialogs

    def add_human_utterances(self, dialogs: Sequence[Dialog], texts: Sequence[str], date_times: Sequence[datetime],
                             annotations: Optional[Sequence[dict]] = None,
                             selected_skills: Optional[Sequence[dict]] = None) -> None:
        if annotations is None:
            annotations = [None] * len(texts)

        if selected_skills is None:
            selected_skills = [None] * len(texts)

        for dialog, text, anno, date_time, ss in zip(dialogs, texts, annotations, date_times, selected_skills):
            utterance = self.create_new_human_utterance(text, dialog.user, date_time, anno, ss)
            dialog.utterances.append(utterance)
            dialog.save()

    def add_bot_utterances(self, dialogs: Sequence[Dialog], orig_texts: Sequence[str], texts: Sequence[str],
                           date_times: Sequence[datetime], active_skills: Sequence[str],
                           confidences: Sequence[float], annotations: Optional[Sequence[dict]] = None) -> None:
        if annotations is None:
            annotations = [None] * len(dialogs)

        for dialog, orig_text, text, date_time, active_skill, confidence, anno in zip(dialogs, orig_texts, texts,
                                                                                      date_times, active_skills,
                                                                                      confidences, annotations):
            utterance = self.create_new_bot_utterance(orig_text, text, dialog.bot, date_time, active_skill, confidence,
                                                     anno)
            dialog.utterances.append(utterance)
            dialog.save()

    @staticmethod
    def add_annotations(utterances: Sequence[Utterance], annotations: Sequence[Dict]):
        for utt, ann in zip(utterances, annotations):
            utt.annotations = ann
            utt.save()

    @staticmethod
    def create_new_dialog(user, bot, location=None, channel_type=None):
        dialog = Dialog(user=user,
                        bot=bot,
                        location=location or Dialog.location.default,
                        channel_type=channel_type)
        dialog.save()
        return dialog

    @staticmethod
    def create_new_human(user_telegram_id, device_type, personality=None, profile=None):
        human = Human(user_telegram_id=user_telegram_id,
                      device_type=device_type,
                      personality=personality,
                      profile=profile or Human.profile.default)
        human.save()
        return human

    @staticmethod
    def create_new_human_utterance(text, user, date_time, annotations=None, selected_skills=None):
        if isinstance(user, Bot):
            raise RuntimeError(
                'Utterances of bots should be created with different method. See create_new_bot_utterance()')
        utt = HumanUtterance(text=text,
                             user=user,
                             date_time=date_time,
                             annotations=annotations or HumanUtterance.annotations.default,
                             selected_skills=selected_skills or HumanUtterance.selected_skills.default)
        utt.save()
        return utt

    @staticmethod
    def create_new_bot_utterance(orig_text, text, user, date_time, active_skill, confidence, annotations=None):
        utt = BotUtterance(orig_text=orig_text,
                           text=text,
                           user=user,
                           date_time=date_time,
                           active_skill=active_skill,
                           confidence=confidence,
                           annotations=annotations or BotUtterance.annotations.default)
        utt.save()
        return utt

    @staticmethod
    def update_me_object(me_obj, kwargs):
        me_obj.modify(**kwargs)
        me_obj.save()

    @staticmethod
    def update_user_profile(me_user, profile):
        me_user.profile.update(**profile)
        me_user.save()
