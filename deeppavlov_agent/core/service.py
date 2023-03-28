from typing import Dict, Any, Optional, Callable, Union, Type, Set, List
from importlib import import_module

from typing_extensions import Literal

from .config import ServiceConfig
from .connectors import Connector
from .state_manager import BaseStateManager
from ..state_formatters import all_formatters


class Service:
    def __init__(
        self,
        name,
        connector_func,
        state_processor_method=None,
        batch_size=1,
        tags=None,
        names_previous_services=None,
        names_required_previous_services=None,
        workflow_formatter=None,
        dialog_formatter=None,
        response_formatter=None,
        label=None,
    ):
        self.name = name
        self.batch_size = batch_size
        self.state_processor_method = state_processor_method
        self.names_previous_services = names_previous_services or set()
        self.names_required_previous_services = (
            names_required_previous_services or set()
        )
        self.tags = set(tags or [])
        self.workflow_formatter = workflow_formatter
        self.dialog_formatter = dialog_formatter
        self.response_formatter = response_formatter
        self.connector_func = connector_func
        self.previous_services = set()
        self.required_previous_services = set()
        self.dependent_services = set()
        self.next_services = set()
        self.label = label or self.name

    def is_sselector(self):
        return "selector" in self.tags

    def is_responder(self):
        return "responder" in self.tags

    def is_input(self):
        return "input" in self.tags

    def is_last_chance(self):
        return "last_chance" in self.tags

    def is_timeout(self):
        return "timeout" in self.tags

    def apply_workflow_formatter(self, payload):
        if not self.workflow_formatter:
            return payload
        return self.workflow_formatter(payload)

    def apply_dialog_formatter(self, payload):
        if not self.dialog_formatter:
            return [self.apply_workflow_formatter(payload)]
        return self.dialog_formatter(self.apply_workflow_formatter(payload))

    def apply_response_formatter(self, payload):
        if not self.response_formatter:
            return payload
        return self.response_formatter(payload)


def simple_workflow_formatter(workflow_record):
    return workflow_record["dialog"].to_dict()


def _get_connector(
    service_name: str, config: ServiceConfig, connectors: Dict[str, Connector]
) -> Connector:
    connector_conf = config.get("connector", None)

    connector: Optional[Connector] = None

    if isinstance(connector_conf, str):
        connector = connectors.get(connector_conf, None)
    elif isinstance(connector_conf, dict):
        connector = connectors.get(service_name, None)

    if connector is None:
        raise ValueError(f"connector in pipeline.{service_name} is not declared")

    return connector


def _get_state_manager_method(
    service_name: str, config: ServiceConfig, state_manager: BaseStateManager
) -> Optional[Callable[..., Any]]:
    sm_method_name = config.get("state_manager_method", None)
    sm_method: Optional[Callable[..., Any]] = None

    if sm_method_name is not None:
        sm_method = getattr(state_manager, sm_method_name, None)

        if not sm_method:
            raise ValueError(
                f"state manager doesn't have a method {sm_method_name} (declared in {service_name})"
            )

    return sm_method


FormatterType = Union[Literal["dialog_formatter"], Literal["response_formatter"]]


def _get_formatter_class(class_name) -> Optional[Type[Any]]:
    params = class_name.split(":")
    formatter_class = None

    if len(params) == 2:
        module = import_module(params[0])
        formatter_class = getattr(module, params[1], None)

    return formatter_class


def _get_formatter(
    formatter_type: FormatterType, service_name: str, config: ServiceConfig
) -> Optional[Callable[..., Any]]:
    formatter_name = config.get(formatter_type, None)

    if formatter_name is None:
        return

    if formatter_name in all_formatters:
        formatter = all_formatters[formatter_name]
    else:
        formatter = _get_formatter_class(formatter_name)

    if not formatter:
        raise ValueError(
            f"{formatter_type} {formatter_name} doesn't exist (declared in {service_name})"
        )

    return formatter


def _merge_service_names(
    config_service_names: Union[Set[str], List[str]], service_names: Dict[str, Set[str]]
) -> Set[str]:
    result = set()

    for sn in config_service_names:
        result.update(service_names.get(sn, set()))

    return result


def make_service(
    *,
    name: str,
    group: Optional[str] = None,
    state_manager: BaseStateManager,
    connectors: Dict[str, Connector],
    service_names: Dict[str, Set[str]],
    config: ServiceConfig,
) -> Service:
    service_name = ".".join([i for i in [group, name] if i])
    connector = _get_connector(service_name, config, connectors)

    return Service(
        name=service_name,
        connector_func=connector.send,
        state_processor_method=_get_state_manager_method(name, config, state_manager),
        workflow_formatter=simple_workflow_formatter,
        dialog_formatter=_get_formatter("dialog_formatter", service_name, config),
        response_formatter=_get_formatter("response_formatter", service_name, config),
        names_previous_services=_merge_service_names(
            config.get("previous_services", set()), service_names
        ),
        names_required_previous_services=_merge_service_names(
            config.get("required_previous_services", set()), service_names
        ),
        tags=config.get("tags", []),
    )
