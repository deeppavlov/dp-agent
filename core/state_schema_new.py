import asyncio

from bson.objectid import ObjectId

from datetime import datetime
import uuid
from pprint import pprint

import motor.motor_asyncio


client = motor.motor_asyncio.AsyncIOMotorClient()
db = client.test_database


class MongoObject(object):
    collection = None
    fields = []

    def __init__(self, _id):
        self._id = _id or None
        if not self._id:
            self.temp_id = 'temp__' + uuid.uuid5(uuid.NAMESPACE_DNS, str(id(self))).hex
        else:
            self.temp_id = None
        self._dict = {}

    def to_dict(self):
        if not self._dict:
            self._dict = {
               'id': self.temp_id or str(self._id)
               }
            for f in self.fields:
                self._dict[f] = getattr(self, f, None)
        return self._dict

    @property
    def update_dict(self):
        update_dict = self.to_dict()
        update_dict.pop('id')
        return update_dict

    def set_id(self, _id):
        self._id = _id
        self.temp_id = None
        self._dict = {}


class HumanObject(MongoObject):
    collection = db.users
    fields = ['user_telegram_id', 'device_type', 'persona', 'profile', 'attributes']

    def __init__(self, user_telegram_id, _id=None, device_type=None, persona=None,
                 profile=None, attributes=None, **kwargs):
        super().__init__(_id=_id)
        self.need_save = True
        self.user_telegram_id = user_telegram_id
        self.device_type = device_type or ''
        self.persona = persona or []
        self.profile = profile or {
             'name': None,
             'gender': None,
             'birthdate': None,
             'location': None,
             'home_coordinates': None,
             'work_coordinates': None,
             'occupation': None,
             'income_per_year': None
        }
        self.attributes = attributes or {}

    @classmethod
    async def get_or_create(cls, user_telegram_id):
        query_obj = await cls.collection.find_one({'user_telegram_id': user_telegram_id})
        if query_obj:
            user_object = cls(**query_obj)
            user_object.set_id(query_obj['_id'])
        else:
            user_object = cls(user_telegram_id)
        return user_object

    async def save(self):
        if self._id:
            result = await self.collection.update_one({'_id': self._id}, {'$set': self.update_dict})
            self._dict = {}
        else:
            result = await self.collection.insert_one(self.update_dict)
            self.set_id(result.inserted_id)
            print(type(result.inserted_id))


class BotObject(MongoObject):
    collection = db.users
    fields = ['persona', 'attributes']

    def __init__(self, _id=None, persona=None, attributes=None, **kwargs):
        super().__init__(_id=_id)
        self.need_save = True
        self.persona = persona or []
        self.attributes = attributes or {}

    @classmethod
    async def get_or_create(cls, id):  # TODO(pugin): remove this shit
        query_obj = await cls.collection.find_one({'_id': id})
        if query_obj:
            bot_object = cls(**query_obj)
            bot_object.set_id(query_obj['_id'])
        else:
            bot_object = cls()
        return bot_object

    async def save(self):
        if self._id:
            result = await self.collection.update_one({'_id': self._id}, {'$set': self.update_dict})
            self._dict = {}
        else:
            result = await self.collection.insert_one(self.update_dict)
            self.set_id(result.inserted_id)
            print(type(result.inserted_id))


class HumanUtteranceObject(MongoObject):
    collection = db.utterance
    fields = ['text', 'annotations', 'date_time', 'selected_skills']

    def __init__(self, _id, dialog_id, in_dialog_id, text=None, annotations=None,
                 date_time=None, selected_skills=None):
        super().__init__(_id=_id)
        self.dialog_id = dialog_id
        self.in_dialog_id = in_dialog_id
        self._class = 'human_utterance'

        self.text = text or ''
        self.annotations = annotations or {}
        self.selected_skills = selected_skills or {}
        self.date_time = date_time or datetime.now()

    async def save(self):
        await self.collection.insert_one(self.update_dict)

class BotUtteranceObject(MongoObject):
    collection = db.utterance
    fields = ['text', 'annotations', 'date_time', 'selected_skills', 'orig_text', 'active_skill', 'confidence']

    def __init__(self, _id, dialog_id, in_dialog_id, text=None,
                 orig_text=None, active_skill=None, confidence = None,
                 annotations=None, date_time=None, selected_skills=None):
        super().__init__(_id=_id)
        self.dialog_id = dialog_id
        self.in_dialog_id = in_dialog_id
        self._class = 'bot_utterance'

        self.text = text or ''
        self.orig_text = orig_text or self.text
        self.active_skill = active_skill
        self.confidence = confidence
        self.annotations = annotations or {}
        self.date_time = date_time or datetime.now()

    async def save(self):
        await self.collection.insert_one(self.update_dict)


class DialogObject(MongoObject):
    collections = db.dialog
    fields = []

    def __init__(self, human, _id=None, bot=None, active=True, **kwargs):
        super().__init__(_id=_id)
        self.utterances = []
        self.human = human
        self.bot = bot or BotObject()
        self.active = active

    @classmethod
    def get_or_create(cls, user_telegram_id, dialog_id=None, reset=False):
        user = HumanObject.get_or_create(user_telegram_id)
        if not user._id:
            dialog_obj = cls(human=user)
        else:
            if reset:
                dialog_obj = cls(human=user)
                # do smth to reset active
            else:
                query_obj = cls.collection.find_one({'human': user._id, 'active': True})
                dialog_obj = cls(**query_obj)

        return dialog_obj

async def get_utterances_from_db(dialog_id):
    collection = db.utterance
    utterances = []
    async for document in db.utterance.find({'dialog_id': dialog_id}).sort('in_dialog_id'):
        if document['_class'] == 'human_utterance':
            utterances.append(HumanUtteranceObject(**document))
        elif document['_class'] == 'bot_utterance':
            utterances.append(BotUtteranceObject(**document))

            



TEST_TELEGRAM_ID = '___' + uuid.uuid4().hex


async def main():
    human = await HumanObject.get_or_create(TEST_TELEGRAM_ID)
    human.persona['abc'] = 'def'
    human.location = 'home'
    # print('human before save')
    # pprint(human.to_dict())
    await human.save()
    # print('human after save')
    # pprint(human.to_dict())

    user = await HumanObject.get_or_create(TEST_TELEGRAM_ID)
    # print('human from db')
    # pprint(user.to_dict())
    user.device_type = 'nokia3310'
    await user.save()
    pprint(user.to_dict())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    loop.run_until_complete(main())


