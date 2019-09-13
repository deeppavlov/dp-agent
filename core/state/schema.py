from uuid import uuid4

from mongoengine import DynamicDocument, ReferenceField, ListField, StringField, DynamicField, \
    DateTimeField, FloatField, DictField


class UserMongo(DynamicDocument):
    uuid = StringField(required=True)
    persona = ListField(default=[])

    meta = {'allow_inheritance': True}


class BotMongo(UserMongo):
    pass


class HumanMongo(UserMongo):
    user_telegram_id = StringField(required=True, unique=True, sparse=True)
    device_type = DynamicField()
    profile = DictField(required=True)


class UtteranceMongo(DynamicDocument):
    uuid = StringField(required=True)
    text = StringField(required=True)
    service_responses = DictField(default={})
    annotations = DictField(default={})
    user = ReferenceField(UserMongo, required=True)
    date_time = DateTimeField(required=True)

    meta = {'allow_inheritance': True}


class HumanUtteranceMongo(UtteranceMongo):
    selected_skills = DynamicField(default=[])


class BotUtteranceMongo(UtteranceMongo):
    orig_text = StringField()
    active_skill = StringField()
    user = ReferenceField(BotMongo, required=True)
    confidence = FloatField()


class DialogMongo(DynamicDocument):
    uuid = StringField(required=True)
    location = DynamicField()
    utterances = ListField(ReferenceField(UtteranceMongo), default=[])
    user = ReferenceField(HumanMongo, required=True)
    bot = ReferenceField(BotMongo, required=True)
    channel_type = StringField(choices=['telegram', 'vk', 'facebook', 'cmd_client', 'http_client', 'tests'],
                               default='telegram')

