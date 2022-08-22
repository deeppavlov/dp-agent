import asyncio
from collections import defaultdict
from importlib import import_module
from typing import Dict

import aiohttp

from .core.connectors import (AgentGatewayToServiceConnector,
                              AioQueueConnector, HTTPConnector,
                              QueueListenerBatchifyer, PredefinedOutputConnector,
                              PredefinedTextConnector, ConfidenceResponseSelectorConnector)
from .core.service import Service, simple_workflow_formatter
from .core.state_manager import StateManager
from .core.transport.mapping import GATEWAYS_MAP
from .core.transport.settings import TRANSPORT_SETTINGS
from .state_formatters import all_formatters


built_in_connectors = {
    "PredefinedOutputConnector": PredefinedOutputConnector,
    "PredefinedTextConnector": PredefinedTextConnector,
    "ConfidenceResponseSelectorConnector": ConfidenceResponseSelectorConnector
}


class PipelineConfigParser:
    def __init__(self, state_manager: StateManager, config: Dict):
        self.config = config
        self.state_manager = state_manager
        self.services = []
        self.services_names = defaultdict(set)
        self.last_chance_service = None
        self.timeout_service = None
        self.connectors = {}
        self.workers = []
        self.session = None
        self.gateway = None
        self.imported_modules = {}

        connectors_module_name = self.config.get('connectors_module', None)
        if connectors_module_name:
            self.connectors_module = import_module(connectors_module_name)
        else:
            self.connectors_module = None

        formatters_module_name = self.config.get('formatters_module', None)
        if formatters_module_name:
            self.formatters_module = import_module(formatters_module_name)
        else:
            self.formatters_module = None

        self.fill_connectors()
        self.fill_services()

    def setup_module_from_config(self, name_var):
        module = None
        connectors_module_name = self.config.get(name_var, None)
        if connectors_module_name:
            module = import_module(connectors_module_name)
        return module

    def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def get_gateway(self, on_channel_callback=None, on_service_callback=None):
        if not self.gateway:
            transport_type = TRANSPORT_SETTINGS['transport']['type']
            gateway_cls = GATEWAYS_MAP[transport_type]['agent']
            self.gateway = gateway_cls(config=TRANSPORT_SETTINGS,
                                       on_service_callback=on_service_callback,
                                       on_channel_callback=on_channel_callback)
        return self.gateway

    def get_external_module(self, module_name: str):
        if module_name not in self.imported_modules:
            module = import_module(module_name)
            self.imported_modules[module_name] = module
        else:
            module = self.imported_modules[module_name]
        return module

    def make_connector(self, name: str, data: Dict):
        workers = []
        if data['protocol'] == 'http':
            connector = None
            workers = []
            if 'urllist' in data or 'num_workers' in data or data.get('batch_size', 1) > 1:
                queue = asyncio.Queue()
                batch_size = data.get('batch_size', 1)
                urllist = data.get('urllist', [data['url']] * data.get('num_workers', 1))
                connector = AioQueueConnector(queue)
                for url in urllist:
                    workers.append(QueueListenerBatchifyer(self.get_session(), url, queue, batch_size))
            else:
                connector = HTTPConnector(self.get_session(), data['url'], timeout=data.get("timeout", 0))

        elif data['protocol'] == 'AMQP':
            gateway = self.get_gateway()
            service_name = data.get('service_name') or data['connector_name']
            connector = AgentGatewayToServiceConnector(to_service_callback=gateway.send_to_service,
                                                       service_name=service_name)

        elif data['protocol'] == 'python':
            params = data['class_name'].split(':')
            if len(params) == 1:
                if params[0] in built_in_connectors:
                    connector_class = built_in_connectors[params[0]]
                    module_provided_str = 'in deeppavlov_agent built in connectors'
                elif self.connectors_module:
                    connector_class = getattr(self.connectors_module, params[0], None)
                    module_provided_str = f'in {self.connectors_module.__name__} connectors module'

                if not connector_class:
                    raise ValueError(f"Connector's python class {data['class_name']} from {name} "
                                     f"connector was not found ({module_provided_str})")
            elif len(params) == 2:
                connector_class = getattr(self.get_external_module(params[0]), params[1], None)
            else:
                raise ValueError(f"Expected class description in a `module.submodules:ClassName` form, "
                                 f"but got `{data['class_name']}` (in {name} connector)")
            others = {k: v for k, v in data.items() if k not in {'protocol', 'class_name'}}
            connector = connector_class(**others)

        self.workers.extend(workers)
        self.connectors[name] = connector

    def make_service(self, group: str, name: str, data: Dict):
        def check_ext_module(class_name):
            params = class_name.split(':')
            formatter_class = None
            if len(params) == 2:
                formatter_class = getattr(self.get_external_module(params[0]), params[1], None)
            elif len(params) == 1 and self.formatters_module:
                formatter_class = getattr(self.formatters_module, params[0], None)
            return formatter_class

        connector_data = data.get('connector', None)
        service_name = ".".join([i for i in [group, name] if i])
        if 'workflow_formatter' in data and not data['workflow_formatter']:
            workflow_formatter = None
        else:
            workflow_formatter = simple_workflow_formatter
        connector = None
        if isinstance(connector_data, str):
            connector = self.connectors.get(connector_data, None)
        elif isinstance(connector_data, dict):
            connector = self.connectors.get(service_name, None)
        if not connector:
            raise ValueError(f'connector in pipeline.{service_name} is not declared')

        sm_data = data.get('state_manager_method', None)
        if sm_data:
            sm_method = getattr(self.state_manager, sm_data, None)
            if not sm_method:
                raise ValueError(f"state manager doesn't have a method {sm_data} (declared in {service_name})")
        else:
            sm_method = None

        dialog_formatter = None
        response_formatter = None

        dialog_formatter_name = data.get('dialog_formatter', None)
        response_formatter_name = data.get('response_formatter', None)
        if dialog_formatter_name:
            if dialog_formatter_name in all_formatters:
                dialog_formatter = all_formatters[dialog_formatter_name]
            else:
                dialog_formatter = check_ext_module(dialog_formatter_name)
            if not dialog_formatter:
                raise ValueError(f"formatter {dialog_formatter_name} doesn't exist (declared in {service_name})")
        if response_formatter_name:
            if response_formatter_name in all_formatters:
                response_formatter = all_formatters[response_formatter_name]
            else:
                response_formatter = check_ext_module(response_formatter_name)
            if not response_formatter:
                raise ValueError(f"formatter {response_formatter_name} doesn't exist (declared in {service_name})")

        names_previous_services = set()
        for sn in data.get('previous_services', set()):
            names_previous_services.update(self.services_names.get(sn, set()))
        names_required_previous_services = set()
        for sn in data.get('required_previous_services', set()):
            names_required_previous_services.update(self.services_names.get(sn, set()))
        tags = data.get('tags', [])
        service = Service(
            name=service_name, connector_func=connector.send, state_processor_method=sm_method, tags=tags,
            names_previous_services=names_previous_services,
            names_required_previous_services=names_required_previous_services,
            workflow_formatter=workflow_formatter, dialog_formatter=dialog_formatter,
            response_formatter=response_formatter, label=name)
        if service.is_last_chance():
            self.last_chance_service = service
        elif service.is_timeout():
            self.timeout_service = service
        else:
            self.services.append(service)

    def fill_connectors(self):
        if 'connectors' in self.config:
            for k, v in self.config['connectors'].items():
                v.update({'connector_name': k})
                self.make_connector(f'connectors.{k}', v)

        # collect residual connectors, form skill names
        for k, v in self.config['services'].items():
            if 'connector' in v:  # single service
                if isinstance(v['connector'], dict):
                    if 'protocol' in v['connector']:
                        self.make_connector(k, v['connector'])
                    else:
                        raise ValueError({f'connector in pipeline.{k} is declared incorrectly'})
                elif not isinstance(v['connector'], str):
                    raise ValueError({f'connector in pipeline.{k} is declared incorrectly'})
                self.services_names[k].add(k)
            else:  # grouped services
                for sk, sv in v.items():
                    service_name = f'{k}.{sk}'
                    if isinstance(sv['connector'], dict):
                        if 'protocol' in sv['connector']:
                            self.make_connector(service_name, sv['connector'])
                        else:
                            raise ValueError({f'connector in pipeline.{service_name} is declared incorrectly'})
                    elif not isinstance(sv['connector'], str):
                        raise ValueError({f'connector in pipeline.{service_name} is declared incorrectly'})
                    self.services_names[k].add(service_name)
                    self.services_names[service_name].add(service_name)

    def fill_services(self):
        for k, v in self.config['services'].items():
            if 'connector' in v:  # single service
                self.make_service(None, k, v)
            else:  # grouped services
                for sk, sv in v.items():
                    self.make_service(k, sk, sv)
