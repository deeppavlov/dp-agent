from typing import TypeVar, Any


class MessageBase:
    @classmethod
    def from_json(cls, message_json):
        message_json.pop('msg_type')
        return cls(**message_json)

    def to_json(self) -> dict:
        return self.__dict__


TMessageBase = TypeVar('TMessageBase', bound=MessageBase)


class ServiceTaskMessage(MessageBase):
    msg_type = 'service_task'
    agent_name: str
    task_uuid: str
    dialog: dict

    def __init__(self, agent_name: str, task_uuid: str, dialog: dict) -> None:
        self.msg_type = self.__class__.msg_type
        self.agent_name = agent_name
        self.task_uuid = task_uuid
        self.dialog = dialog


class ServiceResponseMessage(MessageBase):
    msg_type = 'service_response'
    agent_name: str
    task_uuid: str
    service_name: str
    service_instance_id: str
    dialog_id: str
    response: Any

    def __init__(self, agent_name: str, task_uuid: str, service_name: str, service_instance_id: str, dialog_id: str,
                 response: Any) -> None:

        self.msg_type = self.__class__.msg_type
        self.agent_name = agent_name
        self.task_uuid = task_uuid
        self.service_name = service_name
        self.service_instance_id = service_instance_id
        self.dialog_id = dialog_id
        self.response = response


class ToChannelMessage(MessageBase):
    msg_type = 'to_channel_message'
    agent_name: str
    channel_id: str
    user_id: str
    response: str

    def __init__(self, agent_name: str, channel_id: str, user_id: str, response: str) -> None:
        self.msg_type = self.__class__.msg_type
        self.agent_name = agent_name
        self.channel_id = channel_id
        self.user_id = user_id
        self.response = response


class FromChannelMessage(MessageBase):
    msg_type = 'from_channel_message'
    agent_name: str
    channel_id: str
    user_id: str
    utterance: str
    reset_dialog: bool

    def __init__(self, agent_name: str, channel_id: str, user_id: str, utterance: str, reset_dialog: bool) -> None:
        self.msg_type = self.__class__.msg_type
        self.agent_name = agent_name
        self.channel_id = channel_id
        self.user_id = user_id
        self.utterance = utterance
        self.reset_dialog = reset_dialog


_message_wrappers_map = {
    'service_task': ServiceTaskMessage,
    'service_response': ServiceResponseMessage,
    'to_channel_message': ToChannelMessage,
    'from_channel_message': FromChannelMessage
}


def get_transport_message(message_json: dict) -> TMessageBase:
    message_type = message_json['msg_type']

    if message_type not in _message_wrappers_map:
        raise ValueError(f'Unknown transport message type: {message_type}')

    message_wrapper_class: TMessageBase = _message_wrappers_map[message_type]

    return message_wrapper_class.from_json(message_json)
