import asyncio
from logging import getLogger
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from uuid import uuid4

from core.state.schema import HumanMongo, BotMongo, HumanUtteranceMongo, BotUtteranceMongo, DialogMongo


logger = getLogger(__name__)
TMongoSchemaTypes = Union[HumanMongo, BotMongo, HumanUtteranceMongo, BotUtteranceMongo, DialogMongo]


# TODO completely refactor and simplify mongo classes wrapping or better think of appropriate memcache
class SchemaBase:
    # TODO: think of naming not like uuid library
    uuid: str
    orm_instance: Optional[TMongoSchemaTypes]
    _loop: asyncio.AbstractEventLoop
    _save_lock: asyncio.Lock
    _save_calls: int

    def __init__(self, uuid: Optional[str] = None, orm_instance: Optional[TMongoSchemaTypes] = None) -> None:
        self.uuid = uuid or str(uuid4())
        self.orm_instance = orm_instance
        self._loop = asyncio.get_event_loop()
        self._save_lock = asyncio.Lock
        self._save_calls = 0

    async def save(self) -> None:
        if not self.orm_instance:
            await self._create_orm_instance()
        else:
            await self._update_orm_instance()

        self.orm_instance.save()
        logger.debug(f'Saved ORM instance {self.uuid}')

    def to_dict(self) -> Dict:
        raise NotImplementedError

    async def _create_orm_instance(self) -> None:
        raise NotImplementedError

    async def _update_orm_instance(self) -> None:
        raise NotImplementedError

    @classmethod
    async def create_from_orm(cls, orm_instance: Optional[TMongoSchemaTypes]):
        raise NotImplementedError

    @classmethod
    async def get_or_create(cls, *args, **kwargs):
        raise NotImplementedError


class User(SchemaBase):
    persona: List[str]

    def __init__(self, persona: Optional[List[str]] = None, **kwargs) -> None:
        super(User, self).__init__(**kwargs)
        self.persona = persona or []

    def to_dict(self) -> Dict:
        raise NotImplementedError

    async def _create_orm_instance(self) -> None:
        raise NotImplementedError

    async def _update_orm_instance(self) -> None:
        raise NotImplementedError

    @classmethod
    async def create_from_orm(cls, orm_instance: Union[BotMongo, HumanMongo]):
        raise NotImplementedError

    @classmethod
    async def get_or_create(cls, *args, **kwargs):
        raise NotImplementedError


class Bot(User):
    def __init__(self, uuid: Optional[str] = None, orm_instance: Optional[BotMongo] = None) -> None:
        persona = ['Мне нравится общаться с людьми.',
                   'Пару лет назад я окончила вуз с отличием.',
                   'Я работаю в банке.',
                   'В свободное время помогаю пожилым людям в благотворительном фонде',
                   'Люблю путешествовать']

        super(Bot, self).__init__(persona=persona, uuid=uuid, orm_instance=orm_instance)

    def to_dict(self) -> Dict:
        return {'uuid': str(self.uuid),
                'user_type': 'bot',
                'persona': self.persona}

    async def _create_orm_instance(self) -> None:
        self.orm_instance = BotMongo(uuid=self.uuid,
                                     persona=self.persona)
        logger.debug(f'Created ORM instance for bot {self.uuid}')

    async def _update_orm_instance(self) -> None:
        pass

    @classmethod
    async def create_from_orm(cls, orm_instance: BotMongo):
        return cls(uuid=orm_instance.uuid, orm_instance=orm_instance)

    @classmethod
    async def get_or_create(cls):
        bot_query = BotMongo.objects

        if bot_query:
            orm_instance: BotMongo = bot_query[0]
            bot = await cls.create_from_orm(orm_instance=orm_instance)
            logger.debug(f'Loaded bot {bot.uuid}')
        else:
            bot = cls()
            await bot.save()
            logger.debug(f'Created bot {bot.uuid}')

        return bot


class Human(User):
    user_telegram_id: str
    device_type: Optional[str]
    profile: Dict

    def __init__(self, user_telegram_id: str,
                 device_type: Optional[str],
                 uuid: Optional[str] = None,
                 orm_instance: Optional[HumanMongo] = None) -> None:

        super(Human, self).__init__(uuid=uuid, orm_instance=orm_instance)
        self.user_telegram_id = user_telegram_id
        self.device_type = device_type
        self.profile = {
            'name': None,
            'gender': None,
            'birthdate': None,
            'location': None,
            'home_coordinates': None,
            'work_coordinates': None,
            'occupation': None,
            'income_per_year': None
        }

    def to_dict(self) -> Dict:
        return {'uuid': str(self.uuid),
                'user_telegram_id': self.user_telegram_id,
                'user_type': 'human',
                'device_type': str(self.device_type),
                'persona': self.persona,
                'profile': self.profile}

    async def _create_orm_instance(self) -> None:
        self.orm_instance = HumanMongo(uuid=self.uuid,
                                       persona=self.persona,
                                       user_telegram_id=self.user_telegram_id,
                                       device_type=self.device_type,
                                       profile=self.profile)

        logger.debug(f'Created ORM instance for user {self.uuid}')

    async def _update_orm_instance(self) -> None:
        pass

    @classmethod
    async def create_from_orm(cls, orm_instance: HumanMongo):
        return cls(user_telegram_id=orm_instance.user_telegram_id,
                   device_type=orm_instance.device_type,
                   uuid=orm_instance.uuid,
                   orm_instance=orm_instance)

    @classmethod
    async def get_or_create(cls, user_telegram_id: str, device_type: Optional[str]):
        human_query = HumanMongo.objects(user_telegram_id__exact=user_telegram_id)

        if human_query:
            orm_instance: HumanMongo = human_query[0]
            human = await cls.create_from_orm(orm_instance=orm_instance)
            logger.debug(f'Loaded human {human.uuid}')
        else:
            human = cls(user_telegram_id=user_telegram_id, device_type=device_type)
            logger.debug(f'Created human {human.uuid}')

        return human


class Utterance(SchemaBase):
    text: str
    service_responses: Dict[str, Any]
    annotations: Dict[str, Any]
    user: Union[Human, Bot]
    date_time: datetime

    def __init__(self, text: str, user: Union[Human, Bot], date_time: datetime, **kwargs) -> None:
        super(Utterance, self).__init__(**kwargs)
        self.text = text
        self.user = user
        self.date_time = date_time
        self.service_responses = {}
        self.annotations = {}

    def add_service_response(self, service_name: str, service_response: Any) -> None:
        self.service_responses[service_name] = service_response

    def pop_service_response(self, service_name: str) -> Optional[Any]:
        return self.service_responses.pop(service_name, None)

    def add_annotation(self, service_name: str, annotation: Any) -> None:
        self.annotations[service_name] = annotation

    def get_annotation(self, service_name: str) -> Optional[Any]:
        return self.annotations.get(service_name, None)

    def to_dict(self) -> Dict:
        raise NotImplementedError

    async def _create_orm_instance(self) -> None:
        raise NotImplementedError

    async def _update_orm_instance(self) -> None:
        raise NotImplementedError

    @classmethod
    async def create_from_orm(cls, orm_instance: Union[HumanUtteranceMongo, BotUtteranceMongo]):
        raise NotImplementedError

    @classmethod
    async def get_or_create(cls, *args, **kwargs):
        raise NotImplementedError


class HumanUtterance(Utterance):
    selected_skills: List[Dict]

    def __init__(self, text: str,
                 user: Human,
                 date_time: datetime,
                 uuid: Optional[str] = None,
                 orm_instance: Optional[HumanUtteranceMongo] = None) -> None:

        super(HumanUtterance, self).__init__(text=text,
                                             user=user,
                                             date_time=date_time,
                                             uuid=uuid,
                                             orm_instance=orm_instance)

        self.selected_skills = []

    def add_skill_response(self, skill_response: Dict) -> None:
        self.selected_skills.append(skill_response)

    def to_dict(self) -> Dict:
        return {'uuid': str(self.uuid),
                'text': self.text,
                'user_uuid': str(self.user.uuid),
                'service_responses': self.service_responses,
                'annotations': self.annotations,
                'date_time': str(self.date_time),
                'selected_skills': self.selected_skills}

    async def _create_orm_instance(self) -> None:
        self.orm_instance = HumanUtteranceMongo(uuid=self.uuid,
                                                text=self.text,
                                                user=self.user.orm_instance,
                                                date_time=self.date_time,
                                                annotations=self.annotations,
                                                service_responses=self.service_responses,
                                                selected_skills=self.selected_skills)

        logger.debug(f'Created ORM instance for human utterance {self.uuid}')

    async def _update_orm_instance(self) -> None:
        self.orm_instance.annotations = self.annotations
        self.orm_instance.selected_skills = self.selected_skills
        self.orm_instance.service_responses = self.service_responses
        logger.debug(f'Updated ORM instance for human utterance {self.uuid}')

    @classmethod
    async def create_from_orm(cls, orm_instance: HumanUtteranceMongo):
        human_utterance = cls(text=orm_instance.text,
                              user=orm_instance.user,
                              date_time=orm_instance.date_time,
                              uuid=orm_instance.uuid,
                              orm_instance=orm_instance)

        for service_name, service_response in dict(**orm_instance.service_responses).items():
            human_utterance.add_service_response(service_name=service_name, service_response=service_response)

        for service_name, annotation in dict(**orm_instance.annotations).items():
            human_utterance.add_annotation(service_name=service_name, annotation=annotation)

        for skill_response in orm_instance.selected_skills:
            human_utterance.add_skill_response(skill_response=skill_response)

        return human_utterance

    @classmethod
    async def get_or_create(cls, text: str, user: Human, date_time: datetime):
        human_utterance = cls(text=text, user=user, date_time=date_time)
        logger.debug(f'Created human utterance {human_utterance.uuid}')
        return human_utterance


class BotUtterance(Utterance):
    orig_text: str
    active_skill: str
    confidence: float

    def __init__(self, user: Bot,
                 date_time: datetime,
                 orig_text: str,
                 active_skill: str,
                 confidence: float,
                 uuid: Optional[str] = None,
                 orm_instance: Optional[BotUtteranceMongo] = None) -> None:

        super(BotUtterance, self).__init__(text=orig_text,
                                           user=user,
                                           date_time=date_time,
                                           uuid=uuid,
                                           orm_instance=orm_instance)

        self.orig_text = orig_text
        self.active_skill = active_skill
        self.confidence = confidence

    def set_text(self, text: str) -> None:
        self.text = text

    def to_dict(self) -> Dict:
        return {
            'uuid': str(self.uuid),
            'active_skill': self.active_skill,
            'confidence': self.confidence,
            'text': self.text,
            'orig_text': self.orig_text,
            'user_uuid': str(self.user.uuid),
            'service_responses': self.service_responses,
            'annotations': self.annotations,
            'date_time': str(self.date_time)
        }

    async def _create_orm_instance(self) -> None:
        self.orm_instance = BotUtteranceMongo(uuid=self.uuid,
                                              text=self.text,
                                              user=self.user.orm_instance,
                                              date_time=self.date_time,
                                              annotations=self.annotations,
                                              service_responses=self.service_responses,
                                              orig_text=self.orig_text,
                                              active_skill=self.active_skill,
                                              confidence=self.confidence)

        logger.debug(f'Created ORM instance for bot utterance {self.uuid}')

    async def _update_orm_instance(self) -> None:
        self.orm_instance.text = self.text
        logger.debug(f'Updated ORM instance for bot utterance {self.uuid}')

    @classmethod
    async def create_from_orm(cls, orm_instance: BotUtteranceMongo):
        bot_utterance = cls(user=orm_instance.user,
                            date_time=orm_instance.date_time,
                            orig_text=orm_instance.orig_text,
                            active_skill=orm_instance.active_skill,
                            confidence=orm_instance.confidence,
                            uuid=orm_instance.uuid,
                            orm_instance=orm_instance)

        for service_name, service_response in dict(**orm_instance.service_responses).items():
            bot_utterance.add_service_response(service_name=service_name, service_response=service_response)

        for service_name, annotation in dict(**orm_instance.annotations).items():
            bot_utterance.add_annotation(service_name=service_name, annotation=annotation)

        bot_utterance.set_text(orm_instance.text)

        return bot_utterance

    @classmethod
    async def get_or_create(cls, user: Bot, date_time: datetime, orig_text: str, active_skill: str, confidence: float):
        bot_utterance = cls(user=user,
                            date_time=date_time,
                            orig_text=orig_text,
                            active_skill=active_skill,
                            confidence=confidence)

        logger.debug(f'Created bot utterance {bot_utterance.uuid}')
        return bot_utterance


class Dialog(SchemaBase):
    location: Any
    utterances: List[Union[HumanUtterance, BotUtterance]]
    user: Human
    bot: Bot
    channel_type: str

    def __init__(self, location: Any,
                 user: Human,
                 bot: Bot,
                 channel_type: str,
                 uuid: Optional[str] = None,
                 orm_instance: Optional[DialogMongo] = None) -> None:

        super(Dialog, self).__init__(uuid=uuid, orm_instance=orm_instance)
        self.location = location
        self.user = user
        self.bot = bot

        if channel_type not in ['telegram', 'vk', 'facebook', 'cmd_client', 'http_client', 'tests']:
            raise ValueError(f'Not supported channel type: {channel_type}')
        else:
            self.channel_type = channel_type

        self.utterances = []

    def add_utterance(self, utterance: Union[HumanUtterance, BotUtterance]) -> None:
        self.utterances.append(utterance)

    def to_dict(self) -> Dict:
        return {
            'uuid': str(self.uuid),
            'location': str(self.location),
            'utterances': [utt.to_dict() for utt in self.utterances],
            'user': self.user.to_dict(),
            'bot': self.bot.to_dict(),
            'channel_type': self.channel_type
        }

    async def _create_orm_instance(self) -> None:
        await self.user.save()

        for utterance in self.utterances:
            await utterance.save()

        user_orm_instance = self.user.orm_instance
        bot_orm_instance = self.bot.orm_instance
        utt_orm_instances = [utterance.orm_instance for utterance in self.utterances]

        self.orm_instance = DialogMongo(uuid=self.uuid,
                                        location=self.location,
                                        channel_type=self.channel_type,
                                        user=user_orm_instance,
                                        bot=bot_orm_instance,
                                        utterances=utt_orm_instances)

        logger.debug(f'Created ORM instance for dialog {self.uuid}')

    async def _update_orm_instance(self) -> None:
        for utterance in self.utterances:
            await utterance.save()

        utt_orm_instances = [utterance.orm_instance for utterance in self.utterances]
        self.orm_instance.utterances = utt_orm_instances
        logger.debug(f'Updated ORM instance for dialog {self.uuid}')

    @classmethod
    async def create_from_orm(cls, orm_instance: DialogMongo):
        user = await User.create_from_orm(orm_instance.user)
        bot = await Bot.create_from_orm(orm_instance.bot)

        dialog = cls(location=orm_instance.location,
                     user=user,
                     bot=bot,
                     channel_type=orm_instance.channel_type,
                     uuid=orm_instance.uuid,
                     orm_instance=orm_instance)

        for utterance_orm in orm_instance.utterances:
            if isinstance(utterance_orm, HumanUtteranceMongo):
                utterance = await HumanUtterance.create_from_orm(utterance_orm)
            else:
                utterance = await BotUtterance.create_from_orm(utterance_orm)

            dialog.add_utterance(utterance)

        return dialog

    @classmethod
    async def get_or_create(cls, location: Any, user: Human, bot: Bot, channel_type: str):
        user_orm_instance = user.orm_instance
        dialog_query = DialogMongo.objects(user__exact=user_orm_instance) if user_orm_instance else []

        if dialog_query:
            orm_instance = dialog_query[0]
            dialog = await cls.create_from_orm(orm_instance)
            logger.debug(f'Loaded dialog {dialog.uuid}')
        else:
            dialog = cls(location=location, user=user, bot=bot, channel_type=channel_type)
            logger.debug(f'Created dialog {dialog.uuid}')

        return dialog
