import asyncio
from collections import defaultdict
from importlib import import_module
from typing import Dict, List

import aiohttp

from core.connectors import *
from core.service import Service, simple_workflow_formatter
from core.state_manager import StateManager
from state_formatters import all_formatters


def parse_pipeline_config(config: Dict, state_manager: StateManager, session)-> List:
    session = None
    def make_connector(data: Dict, session):
        workers = []
        if data['protocol'] == 'http':
            connector = None
            workers = []
            if not session:
                session = aiohttp.ClientSession()
            if 'urllist' in data or 'num_workers' in data or data.get('batch_size', 1) > 1:
                queue = asyncio.Queue()
                batch_size = data.get('batch_size', 1)
                urllist = data.get('urllist', [data['url']] * data.get('num_workers', 1))
                connector = AioQueueConnector(queue)
                for url in urllist:
                    workers.append(QueueListenerBatchifyer(session, url, queue, batch_size))
            else:
                connector = HTTPConnector(session, data['url'])

        elif data['protocol'] == 'python':
            params = data['class_name'].split(':')
            if len(params) == 1:
                connector_class = getattr(import_module('core.connectors'), params[0])
            elif len(params) == 2:
                connector_class = getattr(import_module(params[0]), params[1])
            else:
                raise ValueError(f"Expected class description in a `module.submodules:ClassName` form, but got `{data['class_name']}`")
            others = {k: v for k, v in data.items() if k not in {'protocol', 'class_name'}}
            connector = connector_class(**others)
        
        return connector, workers

    def make_service(group, name, data: Dict, connectors: Dict, state_manager: StateManager, services_names: Dict):
        connector_data = data.get('connector', None)
        service_name = ".".join([i for i in [group, name] if i])
        if 'workflow_formatter' in data and not data['workflow_formatter']:
            workflow_formatter = None
        else:
            workflow_formatter = simple_workflow_formatter
        connector = None
        if isinstance(connector_data, str):
            connector = connectors.get(connector_data, None)
        elif isinstance(connector_data, dict):
            connector = connectors.get(service_name, None)
        if not connector:
            raise ValueError(f'connector in pipeline.{service_name} is not declared')
        
        sm_data = data.get('state_manager_method', None)
        if sm_data:
            sm_method = getattr(state_manager, sm_data, None)
            if not sm_method:
                raise ValueError(f"state manager doesn't have a method {sm_data} (declared in {service_name})")
        else:
            sm_method = None
        
        dialog_formatter = None
        response_formatter = None

        dialog_formatter_name = data.get('dialog_formatter', None)
        response_formatter_name = data.get('response_formatter', None)
        if dialog_formatter_name:
            if dialog_formatter_name in dialog_formatter_name:
                dialog_formatter = all_formatters[dialog_formatter_name]
            else:
                raise ValueError(f"formatter {dialog_formatter_name} doesn't exist (declared in {service_name})")
        if response_formatter_name:
            if response_formatter_name in all_formatters:
                response_formatter = all_formatters[response_formatter_name]
            else:
                raise ValueError(f"formatter {response_formatter_name} doesn't exist (declared in {service_name})")
        names_previous_services = set()
        for sn in data.get('previous_services', set()):
            names_previous_services.update(services_names.get(sn, set()))
        tags = data.get('tags', [])
        return Service(name=service_name, connector_func=connector.send, state_processor_method=sm_method, tags=tags,
                       names_previous_services=names_previous_services, workflow_formatter=workflow_formatter,
                       dialog_formatter=dialog_formatter, response_formatter=response_formatter, label=name)

    connectors = {}
    workers = []
    services = []
    services_names = defaultdict(set)

    # fill connectors

    for k, v in config['connectors'].items():
        c, w = make_connector(v, session)
        connectors[f'connectors.{k}'] = c
        workers.extend(w)

    # collect residual connectors, form skill names
    for k, v in config['services'].items():
        if 'connector' in v:  # single service
            if isinstance(v['connector'], dict):
                if 'protocol' in v['connector']:
                    c, w = make_connector(v['connector'], session)
                    connectors[k] = c
                    workers.extend(w)
                else:
                    raise ValueError({f'connector in pipeline.{k} is declared incorrectly'})
            elif not isinstance(v['connector'], str):
                raise ValueError({f'connector in pipeline.{k} is declared incorrectly'})
            services_names[k].add(k)
        else: # grouped services
            for sk, sv in v.items():
                service_name = f'{k}.{sk}'
                if isinstance(sv['connector'], dict):
                    if 'protocol' in sv['connector']:
                        c, w = make_connector(sv['connector'], session)
                        connectors[service_name] = c
                        workers.extend(w)
                    else:
                        raise ValueError({f'connector in pipeline.{service_name} is declared incorrectly'})
                elif not isinstance(sv['connector'], str):
                    raise ValueError({f'connector in pipeline.{service_name} is declared incorrectly'})
                services_names[k].add(service_name)
    # make services

    for k, v in config['services'].items():
        if 'connector' in v:  # single service
            services.append(make_service(None, k, v, connectors, state_manager, services_names))
        else:  # grouped services
            for sk, sv in v.items():
                services.append(make_service(k, sk, sv, connectors, state_manager, services_names))

    return services, workers, session       
