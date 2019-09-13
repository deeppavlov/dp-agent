from mongoengine import DynamicDocument, ReferenceField, ListField, StringField, DynamicField, \
    DateTimeField, FloatField, DictField


class User(DynamicDocument):
    uuid = StringField(required=True)
    persona = ListField(default=[])

    meta = {'allow_inheritance': True}


class Bot(User):
    pass


class Human(User):
    user_telegram_id = StringField(required=True, unique=True, sparse=True)
    device_type = DynamicField()
    profile = DictField(required=True)


class Utterance(DynamicDocument):
    uuid = StringField(required=True)
    text = StringField(required=True)
    service_responses = DictField(default={})
    annotations = DictField(default={})
    user = ReferenceField(User, required=True)
    date_time = DateTimeField(required=True)

    meta = {'allow_inheritance': True}


class HumanUtterance(Utterance):
    selected_skills = DynamicField(default=[])


class BotUtterance(Utterance):
    orig_text = StringField()
    active_skill = StringField()
    user = ReferenceField(Bot, required=True)
    confidence = FloatField()


class Dialog(DynamicDocument):
    uuid = StringField(required=True)
    location = DynamicField()
    utterances = ListField(ReferenceField(Utterance), default=[])
    user = ReferenceField(Human, required=True)
    bot = ReferenceField(Bot, required=True)
    channel_type = StringField(choices=['telegram', 'vk', 'facebook', 'cmd_client', 'http_client', 'tests'],
                               default='telegram')

