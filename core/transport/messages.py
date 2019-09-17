from typing import TypeVar


class MessageBase:
    @classmethod
    def from_json(cls, message_json):
        message_type = message_json.pop('type', None)
        if message_type != cls.type:
            raise ValueError(f'Message type is not [{cls.type}]')
        else:
            return cls(**message_json)

    def to_json(self) -> dict:
        return self.__dict__


TMessageBase = TypeVar('TMessageBase', bound=MessageBase)


class ServiceTaskMessage(MessageBase):
    type = 'service_task'
    agent_name: str
    task_uuid: str
    dialog_state: dict

    def __init__(self, agent_name: str, task_uuid: str, dialog_state: dict) -> None:
        self.type = self.__class__.type
        self.agent_name = agent_name
        self.task_uuid = task_uuid
        self.dialog_state = dialog_state


class ServiceResponseMessage(MessageBase):
    type = 'service_response'
    agent_name: str
    task_uuid: str
    service_name: str
    service_instance_id: str
    partial_dialog_state: dict

    def __init__(self, agent_name: str, task_uuid: str, service_name: str, service_instance_id: str,
                 partial_dialog_state: dict) -> None:
        self.type = self.__class__.type
        self.agent_name = agent_name
        self.task_uuid = task_uuid
        self.service_name = service_name
        self.service_instance_id = service_instance_id
        self.partial_dialog_state = partial_dialog_state


# TODO: think about  in/out channel rich content
class ToChannelMessage(MessageBase):
    type = 'to_channel_message'
    agent_name: str
    channel_id: str
    user_id: str
    response: str

    def __init__(self, agent_name: str, channel_id: str, user_id: str, response: str) -> None:
        self.type = self.__class__.type
        self.agent_name = agent_name
        self.channel_id = channel_id
        self.user_id = user_id
        self.response = response


class FromChannelMessage(MessageBase):
    type = 'from_channel_message'
    agent_name: str
    channel_id: str
    user_id: str
    utterance: str
    reset_dialog: bool

    def __init__(self, agent_name: str, channel_id: str, user_id: str, utterance: str, reset_dialog: bool) -> None:
        self.type = self.__class__.type
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
    message_type = message_json['type']

    if message_type not in _message_wrappers_map:
        raise ValueError(f'Unknown transport message type: {message_type}')

    message_wrapper_class: TMessageBase = _message_wrappers_map[message_type]

    return message_wrapper_class.from_json(message_json)
