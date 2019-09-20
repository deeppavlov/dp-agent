from datetime import datetime
from typing import Sequence, Hashable, Any, Optional, Dict

from core.state_schema import Human, Bot, Utterance, HumanUtterance, BotUtterance, Dialog, HUMAN_UTTERANCE_SCHEMA, BOT_UTTERANCE_SCHEMA
from core.connection import state_storage
from core.bot import BOT
from core import VERSION


class StateManager:

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
    def update_user_profile(me_user, profile):
        me_user.profile.update(**profile)
        me_user.save()


    @classmethod
    def get_or_create_user(cls, user_telegram_id=Hashable, user_device_type=Any):
        user_query = Human.objects(user_telegram_id__exact=user_telegram_id)
        if not user_query:
            user = cls.create_new_human(user_telegram_id, user_device_type)
        else:
            user = user_query[0]
        return user

    @classmethod
    def get_or_create_dialog(cls, user, location, channel_type, should_reset=False):
        if should_reset:
            dialog = cls.create_new_dialog(user=user, bot=BOT, location=location,
                                           channel_type=channel_type)
        else:
            exist_dialogs = Dialog.objects(user__exact=user)
            if not exist_dialogs:
                # TODO remove this "if" condition: it should never happen in production, only while testing
                dialog = cls.create_new_dialog(user=user, bot=BOT, location=location,
                                               channel_type=channel_type)
            else:
                dialog = exist_dialogs[0]

        return dialog

    @classmethod
    def add_human_utterance(cls, dialog: Dialog, text: str, date_time: datetime,
                            annotation: Optional[dict] = None,
                            selected_skill: Optional[dict] = None) -> None:
        utterance = cls.create_new_human_utterance(text, dialog.user, date_time, annotation, selected_skill)
        dialog.utterances.append(utterance)
        dialog.save()

    @classmethod
    def add_bot_utterance(cls, dialog: Dialog, orig_text: str,
                          date_time: datetime, active_skill: str,
                          confidence: float, text: str = None, annotation: Optional[dict] = None) -> None:
        if not text:
            text = orig_text
        utterance = cls.create_new_bot_utterance(orig_text, text, dialog.bot, date_time, active_skill, confidence,
                                                 annotation)
        dialog.utterances.append(utterance)
        dialog.save()

    @staticmethod
    def add_annotation(dialog: Dialog, payload: Dict):
        dialog.utterances[-1].annotations.update(payload)
        dialog.utterances[-1].save()

    @staticmethod
    def add_selected_skill(dialog: Dialog, payload: Dict):
        if not dialog.utterances[-1].selected_skills:
            dialog.utterances[-1].selected_skills = {}
        dialog.utterances[-1].selected_skills.update(payload)
        dialog.utterances[-1].save()

    @staticmethod
    def add_text(dialog: Dialog, payload: str):
        dialog.utterances[-1].text = payload
        dialog.utterances[-1].save()

    @classmethod
    def add_bot_utterance_simple(cls, dialog: Dialog, payload: Dict):
        active_skill_name = list(payload.values())[0]
        active_skill = dialog.utterances[-1].selected_skills.get(active_skill_name, None)
        if not active_skill:
            raise ValueError(f'provided {payload} is not valid')

        text = active_skill['text']
        confidence = active_skill['confidence']

        cls.add_bot_utterance(dialog, text, datetime.now(), active_skill_name, confidence)

    @staticmethod
    def do_nothing(*args, **kwargs):  # exclusive workaround for skill selector
        pass

    @classmethod
    def add_human_utterance_dict(cls, dialog: Dict, text: str, date_time: datetime,
                                 annotation: Optional[dict] = None,
                                 selected_skill: Optional[dict] = None, **kwargs) -> None:
        utterance = HUMAN_UTTERANCE_SCHEMA
        utterance['text'] = text
        utterance['date_time'] = date_time
        dialog['utterances'].append(utterance)

    @classmethod
    def add_human_utterance_simple_dict(cls, dialog: Dict, dialog_object: Dialog, payload: Dict, **kwargs) -> None:
        utterance = HUMAN_UTTERANCE_SCHEMA
        utterance['text'] = payload
        utterance['date_time'] = str(datetime.now())
        utterance['user_id'] = str(dialog_object.user.id)
        dialog['utterances'].append(utterance)

    @classmethod
    def add_bot_utterance_simple_dict(cls, dialog: Dict, dialog_object: Dialog, payload: Dict, **kwargs) -> None:
        active_skill_name = list(payload.values())[0]
        active_skill = dialog['utterances'][-1]['selected_skills'].get(active_skill_name, None)
        if not active_skill:
            raise ValueError(f'provided {payload} is not valid')

        utterance = BOT_UTTERANCE_SCHEMA
        utterance['text'] = active_skill['text']
        utterance['orig_text'] = active_skill['text']
        utterance['date_time'] = str(datetime.now())
        utterance['active_skill'] = active_skill_name
        utterance['confidence'] = active_skill['confidence']
        utterance['user_id'] = str(BOT.id)
        dialog['utterances'].append(utterance)

    @staticmethod
    def add_annotation_dict(dialog: Dict, dialog_object: Dialog, payload: Dict, **kwargs):
        dialog['utterances'][-1]['annotations'].update(payload)

    @staticmethod
    def add_selected_skill_dict(dialog: Dict, dialog_object: Dialog, payload: Dict, **kwargs):
        dialog['utterances'][-1]['selected_skills'].update(payload)

    @staticmethod
    def add_text(dialog: Dict, payload: str):
        dialog['utterances'][-1]['text'] = payload

    @staticmethod
    def save_dialog_dict(dialog: Dict, dialog_object: Dialog, payload=None):
        utt_objects = []
        for utt in dialog['utterances'][::-1]:
            if not utt['id']:
                if utt['type'] == 'human':
                    utt_objects.append(HumanUtterance.from_dict(utt))
                elif utt['type'] == 'bot':
                    utt_objects.append(BotUtterance.from_dict(utt))
                else:
                    raise ValueError('utterance of unknown type')
            else:
                break
        for utt in utt_objects[::-1]:
            dialog_object.utterances.append(utt)

        dialog_object.save()
