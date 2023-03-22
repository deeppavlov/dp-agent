import logging
from collections import defaultdict
from importlib import import_module
from typing import Dict, List, Set, Optional, Any
from types import ModuleType

import aiohttp

from .core.connectors import (
    PredefinedOutputConnector,
    PredefinedTextConnector,
    ConfidenceResponseSelectorConnector,
    make_connector,
)
from .core.service import Service, simple_workflow_formatter
from .core.state_manager import StateManager
from .core.transport.mapping import GATEWAYS_MAP
from .core.transport.settings import TRANSPORT_SETTINGS
from .core.config import (
    parse as parse_conf,
    is_service,
    is_connector,
    ConnectorConfig,
    ServiceConfig,
    Node,
)
from .state_formatters import all_formatters

logger = logging.getLogger(__name__)

built_in_connectors = {
    "PredefinedOutputConnector": PredefinedOutputConnector,
    "PredefinedTextConnector": PredefinedTextConnector,
    "ConfidenceResponseSelectorConnector": ConfidenceResponseSelectorConnector,
}


class PipelineConfigParser:
    def __init__(self, state_manager: StateManager, config: Dict):
        self.state_manager = state_manager
        self.services: List[Service] = []
        self.services_names: Dict[str, Set[str]] = defaultdict(set)
        self.last_chance_service: Optional[Service] = None
        self.timeout_service: Optional[Service] = None
        self.connectors: Dict[str, Any] = {}
        self.workers: List[Any] = []
        self.session = None
        self.gateway = None
        self.imported_modules: Dict[str, ModuleType] = {}
        self.formatters_module: Optional[ModuleType] = None

        formatters_module_name = config.get("formatters_module", None)
        if formatters_module_name:
            self.formatters_module = import_module(formatters_module_name)

        self.parse(config)

    def parse(self, data) -> None:
        for node in parse_conf(data):
            if is_service(node):
                if node.config.get("is_enabled", True) is False:
                    continue

                name = _get_service_name(node)
                group = _get_service_group(node)

                # TODO: strange collection(services_names) refactor this
                if group is None:
                    self.services_names[name].add(name)
                else:
                    self.services_names[group].add(name)
                    self.services_names[name].add(name)

                self.make_service(group, name, node.config)
            elif is_connector(node):
                connector, workers = make_connector(node.config)
                self.workers.extend(workers)
                self.connectors[_get_connector_name(node)] = connector

    def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def get_gateway(self, on_channel_callback=None, on_service_callback=None):
        if not self.gateway:
            transport_type = TRANSPORT_SETTINGS["transport"]["type"]
            gateway_cls = GATEWAYS_MAP[transport_type]["agent"]
            self.gateway = gateway_cls(
                config=TRANSPORT_SETTINGS,
                on_service_callback=on_service_callback,
                on_channel_callback=on_channel_callback,
            )
        return self.gateway

    def get_external_module(self, module_name: str):
        if module_name not in self.imported_modules:
            module = import_module(module_name)
            self.imported_modules[module_name] = module
        else:
            module = self.imported_modules[module_name]
        return module

    def make_service(self, group: Optional[str], name: str, data: ServiceConfig):
        logger.debug(f"Create service: '{name}' config={data}")

        def check_ext_module(class_name):
            params = class_name.split(":")
            formatter_class = None
            if len(params) == 2:
                formatter_class = getattr(
                    self.get_external_module(params[0]), params[1], None
                )
            elif len(params) == 1 and self.formatters_module:
                formatter_class = getattr(self.formatters_module, params[0], None)
            return formatter_class

        connector_data = data.get("connector", None)
        service_name = ".".join([i for i in [group, name] if i])
        if "workflow_formatter" in data and not data["workflow_formatter"]:
            workflow_formatter = None
        else:
            workflow_formatter = simple_workflow_formatter
        connector = None
        if isinstance(connector_data, str):
            connector = self.connectors.get(connector_data, None)
        elif isinstance(connector_data, dict):
            connector = self.connectors.get(service_name, None)
        if not connector:
            raise ValueError(f"connector in pipeline.{service_name} is not declared")

        sm_data = data.get("state_manager_method", None)
        if sm_data:
            sm_method = getattr(self.state_manager, sm_data, None)
            if not sm_method:
                raise ValueError(
                    f"state manager doesn't have a method {sm_data} (declared in {service_name})"
                )
        else:
            sm_method = None

        dialog_formatter = None
        response_formatter = None

        dialog_formatter_name = data.get("dialog_formatter", None)
        response_formatter_name = data.get("response_formatter", None)
        if dialog_formatter_name:
            if dialog_formatter_name in all_formatters:
                dialog_formatter = all_formatters[dialog_formatter_name]
            else:
                dialog_formatter = check_ext_module(dialog_formatter_name)
            if not dialog_formatter:
                raise ValueError(
                    f"formatter {dialog_formatter_name} doesn't exist (declared in {service_name})"
                )
        if response_formatter_name:
            if response_formatter_name in all_formatters:
                response_formatter = all_formatters[response_formatter_name]
            else:
                response_formatter = check_ext_module(response_formatter_name)
            if not response_formatter:
                raise ValueError(
                    f"formatter {response_formatter_name} doesn't exist (declared in {service_name})"
                )

        names_previous_services = set()
        for sn in data.get("previous_services", set()):
            names_previous_services.update(self.services_names.get(sn, set()))
        names_required_previous_services = set()
        for sn in data.get("required_previous_services", set()):
            names_required_previous_services.update(self.services_names.get(sn, set()))
        tags = data.get("tags", [])
        service = Service(
            name=service_name,
            connector_func=connector.send,
            state_processor_method=sm_method,
            tags=tags,
            names_previous_services=names_previous_services,
            names_required_previous_services=names_required_previous_services,
            workflow_formatter=workflow_formatter,
            dialog_formatter=dialog_formatter,
            response_formatter=response_formatter,
            label=name,
        )
        if service.is_last_chance():
            self.last_chance_service = service
        elif service.is_timeout():
            self.timeout_service = service
        else:
            self.services.append(service)


def _get_connector_name(node: Node[ConnectorConfig]) -> str:
    # service connector
    name = node.path[-2]
    group = node.path[-3]

    # grouped connectors
    if name == "connectors":
        return f"connectors.{node.path[-1]}"
    # service inside group
    if group != "services":
        return f"{group}.{name}"

    return name


def _get_service_name(node: Node[ServiceConfig]) -> str:
    return node.path[-1]


def _get_service_group(node: Node[ServiceConfig]) -> Optional[str]:
    group = node.path[-2]

    if group == "services":
        return None

    return group
