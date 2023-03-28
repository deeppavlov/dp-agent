import logging
from collections import defaultdict
from typing import Dict, List, Set, Optional, Any
from types import ModuleType

from .core.connectors import make_connector
from .core.service import Service, make_service
from .core.state_manager import StateManager
from .core.config import (
    parse as parse_conf,
    is_service,
    is_connector,
    ConnectorConfig,
    ServiceConfig,
    Node,
)

logger = logging.getLogger(__name__)


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

                logger.debug(f"Create service: '{name}' config={node.config}")

                service = make_service(
                    name=name,
                    group=group,
                    state_manager=self.state_manager,
                    connectors=self.connectors,
                    service_names=self.services_names,
                    config=node.config,
                )

                if service.is_last_chance():
                    self.last_chance_service = service
                elif service.is_timeout():
                    self.timeout_service = service
                else:
                    self.services.append(service)
            elif is_connector(node):
                name = _get_connector_name(node)
                logger.debug(f"Create connector: '{name}' config={node.config}")
                connector, workers = make_connector(node.config)
                self.workers.extend(workers)
                self.connectors[name] = connector


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
