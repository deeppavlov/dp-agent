from typing import Iterator, Any, Union, Dict, List, TypeVar, Generic
from dataclasses import dataclass

from typing_extensions import NotRequired, TypedDict, TypeGuard, Literal


Annotation = Dict[str, Union[str, List[str]]]


class ConnectorConfig(TypedDict):
    protocol: Union[Literal["http"], Literal["python"], Literal["AMQP"]]
    class_name: NotRequired[str]
    response_text: NotRequired[str]
    annotator_names: NotRequired[List[str]]
    annotations: NotRequired[Dict[str, Annotation]]
    timeout: NotRequired[int]
    url: NotRequired[str]
    connector_name: NotRequired[str]
    num_workers: NotRequired[int]
    batch_size: NotRequired[int]
    urllist: NotRequired[List[str]]
    service_name: NotRequired[str]


class ServiceConfig(TypedDict):
    connector: Union[ConnectorConfig, str]
    dialog_formatter: NotRequired[str]
    response_formatter: NotRequired[str]
    state_manager_method: NotRequired[str]
    tags: NotRequired[List[str]]
    previous_services: NotRequired[List[str]]
    required_previous_services: NotRequired[List[str]]
    workflow_formatter: NotRequired[str]
    is_enabled: NotRequired[bool]


ConfT = TypeVar("ConfT", ConnectorConfig, ServiceConfig, Dict)


@dataclass
class Node(Generic[ConfT]):
    config: ConfT
    path: List[str]


def is_service(node: Node) -> TypeGuard[Node[ServiceConfig]]:
    return "connector" in node.config


def is_connector(node: Node) -> TypeGuard[Node[ConnectorConfig]]:
    return "protocol" in node.config


def traverse(root: Node) -> Iterator[Node]:
    for key, val in root.config.items():
        curr_path = root.path + [key]

        if not isinstance(val, dict):
            continue

        node = Node(config=val, path=curr_path)

        # first find all the connectors
        if not is_connector(node):
            yield from traverse(node)

        if is_service(node) or is_connector(node):
            yield node


def parse(data: Any) -> Iterator[Node]:
    assert isinstance(data, dict), "Config must be a dictionary"
    yield from traverse(Node(config=data, path=[]))
