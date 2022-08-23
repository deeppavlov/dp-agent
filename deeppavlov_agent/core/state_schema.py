import logging
import uuid
from hashlib import md5
from collections import defaultdict
from copy import copy
from datetime import datetime
from itertools import chain

import pymongo
from bson.objectid import ObjectId
import bson.json_util
import json

from . import STATE_API_VERSION

USER_PROFILE = {
    "name": None,
    "gender": None,
    "birthdate": None,
    "location": None,
    "home_coordinates": None,
    "work_coordinates": None,
    "occupation": None,
    "income_per_year": None
}


class HumanUtterance:
    collection_name = 'human_utterance'
    fieldlist = ['text', 'user', 'annotations', 'hypotheses']

    def __init__(self, _in_dialog_id, _dialog_id=None, _id=None, text=None, user=None, utt_id=None,
                 annotations=None, date_time=None, hypotheses=None, actual=False, attributes=None):
        self._id = _id
        self._dialog_id = _dialog_id
        self._in_dialog_id = _in_dialog_id
        self.date_time = date_time or datetime.now()
        self.utt_id = utt_id or md5((str(self.date_time) + str(self._dialog_id) + str(self._in_dialog_id)).encode('utf-8')).hexdigest()
        self.text = text or ''
        self.user = user or {}
        self.annotations = annotations or {}
        self.hypotheses = hypotheses or []
        self.attributes = attributes or {}

        self.actual = actual

    @classmethod
    async def prepare_collection(cls, db):
        await db[cls.collection_name].create_index('_dialog_id')
        await db[cls.collection_name].create_index('date_time')
        await db[cls.collection_name].create_index('utt_id')

    def to_dict(self, force_encode_date=True):
        if force_encode_date:
            dumped_attrs = json.loads(json.dumps(self.attributes, default=bson.json_util.default))
        else:
            dumped_attrs = self.attributes
        return {
            'utt_id': self.utt_id,
            'text': self.text,
            'user': self.user,
            'annotations': self.annotations,
            'hypotheses': self.hypotheses,
            'date_time': str(self.date_time),
            'attributes': dumped_attrs
        }

    async def save(self, db, force_encode_date=True):
        data = self.to_dict(force_encode_date)
        data['date_time'] = self.date_time
        data['_dialog_id'] = self._dialog_id
        data['_in_dialog_id'] = self._in_dialog_id
        if not self._id:
            result = await db[self.collection_name].insert_one(data)
            self._id = result.inserted_id
            self.temp_id = None
        else:
            data.pop('utt_id')
            result = await db[self.collection_name].update_one(
                {'_id': self._id},
                {'$set': data}
            )
        return self._id

    @classmethod
    async def get_many(cls, db, dialog_id):
        result = []
        async for document in db[cls.collection_name].find({'_dialog_id': dialog_id}):
            result.append(cls(actual=True, **document))
        return result

    @classmethod
    async def get_all(cls, db):
        result = []
        async for document in db[cls.collection_name].find():
            result.append(cls(**document))
        return result

    @classmethod
    async def get_by_id(cls, db, utt_id):
        utt = await db[cls.collection_name].find_one({'id': utt_id})
        if utt:
            return cls(**utt)


class BotUtterance:
    collection_name = 'bot_utterance'

    def __init__(self, _in_dialog_id, _dialog_id=None, _id=None, text=None, utt_id=None,
                 user=None, annotations=None, date_time=None, active_skill=None,
                 confidence=None, orig_text=None, actual=False, attributes=None):
        self._id = _id
        self._dialog_id = _dialog_id
        self._in_dialog_id = _in_dialog_id
        self.date_time = date_time or datetime.now()
        self.utt_id = utt_id or md5((str(self.date_time) + str(self._dialog_id) + str(self._in_dialog_id)).encode('utf-8')).hexdigest()
        self.text = text or ''
        self.orig_text = orig_text
        self.active_skill = active_skill or ''
        self.confidence = confidence or 1
        self.user = user or {}
        self.annotations = annotations or {}
        self.actual = actual
        self.attributes = attributes or {}

    @classmethod
    async def prepare_collection(cls, db):
        await db[cls.collection_name].create_index('_dialog_id')
        await db[cls.collection_name].create_index('date_time')
        await db[cls.collection_name].create_index('utt_id')

    def to_dict(self, force_encode_date=True):
        if force_encode_date:
            dumped_attrs = json.loads(json.dumps(self.attributes, default=bson.json_util.default))
        else:
            dumped_attrs = self.attributes
        return {
            'utt_id': self.utt_id,
            'text': self.text,
            'orig_text': self.orig_text,
            'active_skill': self.active_skill,
            'confidence': self.confidence,
            'annotations': self.annotations,
            'date_time': str(self.date_time),
            'user': self.user,
            'attributes': dumped_attrs
        }

    async def save(self, db, force_encode_date=True):
        data = self.to_dict(force_encode_date)
        data['date_time'] = self.date_time
        data['_dialog_id'] = self._dialog_id
        data['_in_dialog_id'] = self._in_dialog_id
        if not self._id:
            result = await db[self.collection_name].insert_one(data)
            self._id = result.inserted_id
        else:
            data.pop('utt_id')
            result = await db[self.collection_name].update_one(
                {'_id': self._id},
                {'$set': data}
            )
        return self._id

    @classmethod
    async def get_many(cls, db, dialog_id):
        result = []
        async for document in db[cls.collection_name].find({'_dialog_id': dialog_id}):
            result.append(cls(actual=True, **document))
        return result

    @classmethod
    async def get_all(cls, db):
        result = []
        async for document in db[cls.collection_name].find():
            result.append(cls(**document))
        return result

    @classmethod
    async def get_by_id(cls, db, utt_id):
        utt = await db[cls.collection_name].find_one({'utt_id': utt_id})
        if utt:
            return cls(**utt)


class Dialog:
    collection_name = 'dialog'
    fieldlist = []

    def __init__(self, human, channel_type, dialog_id=None, _human_id=None, _bot_id=None,
                 _id=None, _active=True, version=None, actual=False,
                 date_start=None, date_finish=None, attributes=None):
        self._id = _id
        self.temp_id = None
        if not _id:
            self.temp_id = uuid.uuid4().hex
        self.human = human
        self._human_id = human._id
        self.dialog_id = dialog_id or md5((str(self._human_id) + str(datetime.now())).encode('utf-8')).hexdigest()
        self.channel_type = channel_type
        self.bot = None
        self._bot_id = _bot_id
        self._active = _active
        self.utterances = []
        self.human_utterances = []
        self.bot_utterances = []
        self.version = version or STATE_API_VERSION
        self._dict = {}
        self.actual = actual
        self.date_start = date_start
        self.date_finish = date_finish
        self.attributes = attributes or {}

    @property
    def id(self):
        return self.dialog_id

    @classmethod
    async def prepare_collection(cls, db):
        await db[cls.collection_name].create_index(
            [
                ('_user_id', pymongo.ASCENDING),
                ('_active', pymongo.DESCENDING)
            ]
        )
        await db[cls.collection_name].create_index(
            [
                ('date_start', pymongo.DESCENDING),
                ('date_finish', pymongo.DESCENDING),
            ]
        )
        await db[cls.collection_name].create_index('date_start')
        await db[cls.collection_name].create_index('date_finish')
        await db[cls.collection_name].create_index('dialog_id')

    def to_dict(self):
        dumped_attrs = json.loads(json.dumps(self.attributes, default=bson.json_util.default))
        return {
            '_id': str(self._id),
            'dialog_id': self.dialog_id,
            'utterances': [i.to_dict() for i in self.utterances],
            'human_utterances': [i.to_dict() for i in self.human_utterances],
            'bot_utterances': [i.to_dict() for i in self.bot_utterances],
            'human': self.human.to_dict(),
            'bot': self.bot.to_dict(),
            'channel_type': self.channel_type,
            'date_start': str(self.date_start),
            'date_finish': str(self.date_finish),
            '_active': str(self._active),
            'attributes': dumped_attrs
        }

    async def load_external_info(self, db):
        if self._id:
            self.human_utterances = await HumanUtterance.get_many(db, self._id)
            self.bot_utterances = await BotUtterance.get_many(db, self._id)
            self.utterances = sorted(chain(self.human_utterances, self.bot_utterances), key=lambda x: x._in_dialog_id)
            self.bot = await Bot.get_or_create(db, self._bot_id)

    @classmethod
    async def get_or_create_by_user(cls, db, human, channel_type):
        if human._id:
            dialog = await db[cls.collection_name].find_one({'_human_id': human._id, '_active': True})
            if dialog:
                dialog_obj = cls(actual=True, human=human, **dialog)
                await dialog_obj.load_external_info(db)
                return dialog_obj
        dialog_obj = cls(_human_id=human._id, human=human, channel_type=channel_type)
        dialog_obj.bot = Bot()
        return dialog_obj

    @classmethod
    async def get_many_by_ext_id(cls, db, external_id=None, human=None):
        if external_id:
            human = await Human.get_or_create(db, external_id)
        if not human:
            raise ValueError('You should provide either external_id or human object')
        result = []
        async for document in db[cls.collection_name].find({'_human_id': human._id}):
            result.append(cls(actual=True, human=human, **document))
            await result[-1].load_external_info(db)
        return result

    @classmethod
    async def get_all(cls, db):
        humans = {i._id: i for i in await Human.get_all(db)}
        bots = {i._id: i for i in await Bot.get_all(db)}
        utterances = defaultdict(list)
        for doc in await HumanUtterance.get_all(db):
            utterances[doc._dialog_id].append(doc)
        for doc in await BotUtterance.get_all(db):
            utterances[doc._dialog_id].append(doc)
        result = []
        async for document in db[cls.collection_name].find():
            dialog = cls(actual=True, human=humans[document['_human_id']], **document)
            dialog.bot = bots[document['_bot_id']]
            dialog.utterances = sorted(utterances[document['_id']], key=lambda x: x._in_dialog_id)
            result.append(dialog)
        return result

    @classmethod
    async def list_ids(cls, db, offset=0, limit=10, **filter_kwargs):
        """
        request list of ids for particular page
        :param db: TODO
        :param offset: int, since each id we need to retrieve
        :param limit: int, how many ids to retrieve
        :param filter_kwargs: dict which is transmitted to mongo find request to filter dialogs
        :return: ?
        """
        result = []
        result_cntr = 0
        # TODO sorting by -date (from recent to old)
        cntr = 0
        async for document in db[cls.collection_name].find(filter_kwargs):
            if cntr<offset:
                cntr += 1
                continue
            result.append(str(document['dialog_id']))
            result_cntr += 1
            cntr += 1
            if result_cntr >= limit:
                break
        return result

    @classmethod
    async def get_by_id(cls, db, dialog_id):
        dialog = await db[cls.collection_name].find_one({'_id': ObjectId(dialog_id)})
        if dialog:
            human = await Human.get_by_id(db, dialog['_human_id'])
            dialog_obj = cls(actual=True, human=human, **dialog)
            await dialog_obj.load_external_info(db)
            return dialog_obj
        return None

    @classmethod
    async def get_by_dialog_id(cls, db, dialog_id, full=False):
        dialog = await db[cls.collection_name].find_one({'dialog_id': dialog_id})
        if dialog:
            human = await Human.get_by_id(db, dialog['_human_id'])
            dialog_obj = cls(actual=True, human=human, **dialog)
            if full:
                await dialog_obj.load_external_info(db)
            return dialog_obj
        return None

    @classmethod
    async def get_active(cls, db, human_id):
        dialog = await db[cls.collection_name].find_one({'_human_id': human_id, '_active': True})
        if dialog:
            return dialog["dialog_id"]

    @classmethod
    async def drop_active(cls, db, human_id):
        dialog = await db[cls.collection_name].find_one({'_human_id': human_id, '_active': True})
        if dialog:
            await db[cls.collection_name].update_one({'_id': dialog['_id']}, {'$set': {'_active': False}})
            return dialog["dialog_id"]

    @classmethod
    async def set_rating_drop_active(cls, db, human_id, rating=None):
        dialog = await db[cls.collection_name].find_one({'_human_id': human_id, '_active': True})
        attributes = dialog["attributes"]
        if rating:
            if 'ratings' not in attributes:
                attributes['ratings'] = []
            attributes['ratings'].append(
                {'rating': rating, 'human_id': human_id, 'datetime': datetime.now()}
            )

        if dialog:
            await db[cls.collection_name].update_one(
                {'_id': dialog['_id']}, {'$set': {'_active': False, 'attributes': attributes}}
            )
            return dialog["dialog_id"]

    @classmethod
    async def get_or_create_by_ext_id(cls, db, external_id, channel_type):
        human = await Human.get_or_create(db, external_id)
        return await cls.get_or_create_by_user(db, human, channel_type)

    @classmethod
    async def get_channels(cls, db):
        return await db[cls.collection_name].distinct('channel_type')

    def add_human_utterance(self):
        ind = 0
        if self.utterances:
            ind = self.utterances[-1]._in_dialog_id + 1
        utterance_obj = HumanUtterance(_in_dialog_id=ind)
        self.utterances.append(utterance_obj)
        self.human_utterances.append(utterance_obj)

    def add_bot_utterance(self):
        ind = 0
        if self.utterances:
            ind = self.utterances[-1]._in_dialog_id + 1
        utterance_obj = BotUtterance(_in_dialog_id=ind)
        self.utterances.append(utterance_obj)
        self.bot_utterances.append(utterance_obj)

    async def save(self, db, force=False):
        self._human_id = await self.human.save(db)
        if self.bot:
            self._bot_id = await self.bot.save(db)
        data = {'attributes': self.attributes}
        if self.utterances:
            data['date_start'] = self.utterances[0].date_time
            data['date_finish'] = self.utterances[-1].date_time
        if not self._id:
            data.update({
                'dialog_id': self.dialog_id,
                '_human_id': self._human_id,
                '_bot_id': self._bot_id,
                '_active': self._active,
                'channel_type': self.channel_type,
            })
            dialog = await db[self.collection_name].insert_one(data)
            self._id = dialog.inserted_id
        else:
            await db[self.collection_name].update_one(
                {'_id': self._id},
                {'$set': data}
            )
        for utt in self.utterances[::-1]:
            if utt.actual and not force:
                break
            utt._dialog_id = self._id
            await utt.save(db, force_encode_date=False)


class Human:
    collection_name = 'user'
    fieldlist = ['persona', 'attributes', 'profile']

    def __init__(self, external_id, _id=None, persona=None,
                 attributes=None, profile=None):
        self._id = _id
        self.temp_id = None
        if not _id:
            self.temp_id = uuid.uuid4().hex
        self.external_id = external_id
        self.persona = persona or {}
        self.attributes = attributes or {}
        self.profile = profile or USER_PROFILE.copy()
        self._dict = {}
        self.prev_state = self.get_state()

    @property
    def id(self):
        if self._id:
            return str(self._id)
        return self.temp_id

    @classmethod
    async def prepare_collection(cls, db):
        await db[cls.collection_name].create_index('external_id')

    def to_dict(self):
        return {
            'id': self.id,
            'user_external_id': self.external_id,
            'persona': self.persona,
            'profile': self.profile,
            'attributes': self.attributes,
            'user_type': 'human'
        }

    def get_state(self):
        result = {'persona': self.persona.copy()}
        result['profile'] = self.profile.copy()
        result['attributes'] = self.attributes.copy()
        return flatten_dict(result)

    @classmethod
    async def get_or_create(cls, db, external_id):
        user = await db[cls.collection_name].find_one({'external_id': external_id})
        if user:
            return cls(**user)
        return cls(external_id=external_id)

    @classmethod
    async def get_by_id(cls, db, id):
        user = await db[cls.collection_name].find_one({'_id': id})
        if user:
            if 'telegram_id' in user:
                user['external_id'] = user['telegram_id']
                del user['telegram_id']
            return cls(**user)
        return None

    @classmethod
    async def get_all(cls, db):
        result = []
        async for document in db[cls.collection_name].find():
            result.append(cls(**document))
        return result

    async def save(self, db):
        is_changed = self.prev_state != self.get_state()
        if not self._id:
            user_obj = await db[self.collection_name].insert_one({
                'external_id': self.external_id,
                'persona': self.persona,
                'profile': self.profile, 'attributes': self.attributes}
            )
            self._id = user_obj.inserted_id
            self.temp_id = None
        elif is_changed:
            user_obj = await db[self.collection_name].update_one({
                '_id': self._id},
                {'$set': {
                    'persona': self.persona,
                    'profile': self.profile,
                    'attributes': self.attributes
                }
            })
        return self._id


class Bot:
    collection_name = 'bot'

    def __init__(self, _id=None, persona=None,
                 attributes=None):
        self._id = _id
        self.temp_id = None
        if not _id:
            self.temp_id = uuid.uuid4().hex
        self.persona = persona or {}
        self.attributes = attributes or {}

        self.prev_state = self.get_state()

    @property
    def id(self):
        if self._id:
            return str(self._id)
        return self.temp_id

    def to_dict(self):
        return {
            'id': self.id,
            'persona': self.persona,
            'attributes': self.attributes,
            'user_type': 'bot'
        }

    def get_state(self):
        result = {'persona': self.persona.copy()}
        result['attributes'] = self.attributes.copy()
        return flatten_dict(result)

    @classmethod
    async def get_or_create(cls, db, id=None):
        if id:
            bot = await db[cls.collection_name].find_one({'_id': id})
            if bot:
                return cls(**bot)
        return cls()

    @classmethod
    async def get_all(cls, db):
        result = []
        async for document in db[cls.collection_name].find():
            result.append(cls(**document))
        return result

    async def save(self, db):
        is_changed = self.prev_state != self.get_state()
        if not self._id:
            bot_obj = await db[self.collection_name].insert_one({
                'persona': self.persona, 'attributes': self.attributes}
            )
            self._id = bot_obj.inserted_id
            self.temp_id = None
        elif is_changed:
            bot_obj = await db[self.collection_name].update_one({
                '_id': self._id},
                {'$set': {
                    'persona': self.persona,
                    'attributes': self.attributes
                }
            })
        return self._id


def flatten_dict(inp, parent_key=None):
    result = {}
    for k, v in inp.items():
        if parent_key:
            key_name = f'{parent_key}.{k}'
        else:
            key_name = k
        if isinstance(v, dict):
            result.update(flatten_dict(v, key_name))
        else:
            result[key_name] = copy(v)
    return result


if __name__ == '__main__':
    pass
