import aiohttp
import asyncio
from functools import partial

from core.transform_config import SKILLS, ANNOTATORS_1, ANNOTATORS_2, ANNOTATORS_3, SKILL_SELECTORS, RESPONSE_SELECTORS, POSTPROCESSORS, HIGHLOAD_SETTINGS
from core.connectors import HTTPConnector, ConfidenceResponseSelectorConnector, AioQueueConnector, QueueListenerBatchifyer
from core.pipeline import Service, simple_workflow_formatter
from core.state_manager import StateManager
from core.transport import transport_map


def parse_old_config(on_channel_callback, on_service_callback):
    services = []
    worker_tasks = []
    _session = None
    _agent_gateway = None

    def make_service_from_config_rec(conf_record, session, state_processor_method, tags,
                                     names_previous_services, agent_gateway, name_modifier=None):
        worker_tasks = []
        connector_callable = None

        if name_modifier:
            name = name_modifier(conf_record['name'])
        else:
            name = conf_record['name']

        formatter = conf_record['formatter']
        batch_size = conf_record.get('batch_size', 1)
        url = conf_record['url']
        url2 = conf_record.get('url2', None)

        if conf_record['protocol'] == 'http':
            session = _session or aiohttp.ClientSession()
            if batch_size == 1 and not url2:
                connector = HTTPConnector(session, url, formatter, conf_record['name'])
            else:
                queue = asyncio.Queue()
                connector = AioQueueConnector(queue)  # worker task and queue connector
                worker_tasks.append(QueueListenerBatchifyer(session, url, formatter, name, queue, batch_size))
                if url2:
                    worker_tasks.append(QueueListenerBatchifyer(session, url2, formatter, name, queue, batch_size))
        elif conf_record['protocol'] == 'highload':
            if not agent_gateway:
                transport_type = HIGHLOAD_SETTINGS['transport']['type']
                gateway_cls = transport_map[transport_type]['agent']
                agent_gateway = gateway_cls(config=HIGHLOAD_SETTINGS,
                                            on_service_callback=on_service_callback,
                                            on_channel_callback=on_channel_callback)
            else:
                agent_gateway = _agent_gateway

            connector = agent_gateway
            connector_callable = partial(agent_gateway.send_to_service, service=name)

        service = Service(name, connector, state_processor_method, batch_size, tags,
                          names_previous_services, simple_workflow_formatter, connector_callable)

        return service, worker_tasks, session, agent_gateway

    def add_bot_to_name(name):
        return f'bot_{name}'

    for anno in ANNOTATORS_1:
        service, workers, _session, _agent_gateway = \
            make_service_from_config_rec(anno, _session, StateManager.add_annotation,
                                         ['ANNOTATORS_1'], set(), _agent_gateway)
        services.append(service)
        worker_tasks.extend(workers)

    previous_services = {i.name for i in services if 'ANNOTATORS_1' in i.tags}

    if ANNOTATORS_2:
        for anno in ANNOTATORS_2:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(anno, _session, StateManager.add_annotation,
                                             ['ANNOTATORS_2'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'ANNOTATORS_2' in i.tags}

    if ANNOTATORS_3:
        for anno in ANNOTATORS_3:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(anno, _session, StateManager.add_annotation,
                                             ['ANNOTATORS_3'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'ANNOTATORS_3' in i.tags}

    if SKILL_SELECTORS:
        for ss in SKILL_SELECTORS:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(ss, _session, StateManager.do_nothing,
                                             ['SKILL_SELECTORS', 'selector'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'SKILL_SELECTORS' in i.tags}

    if SKILLS:
        for s in SKILLS:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(s, _session, StateManager.add_selected_skill,
                                             ['SKILLS'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'SKILLS' in i.tags}

    if not RESPONSE_SELECTORS:
        services.append(Service('confidence_response_selector', ConfidenceResponseSelectorConnector(),
                                StateManager.add_bot_utterance_simple,
                                1, ['RESPONSE_SELECTORS'], previous_services, _agent_gateway, simple_workflow_formatter))
    else:
        for r in RESPONSE_SELECTORS:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(r, _session, StateManager.add_bot_utterance_simple,
                                             ['RESPONSE_SELECTORS'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

    previous_services = {i.name for i in services if 'RESPONSE_SELECTORS' in i.tags}

    if POSTPROCESSORS:
        for p in POSTPROCESSORS:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(p, _session, StateManager.add_text,
                                             ['POSTPROCESSORS'], previous_services, _agent_gateway)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'POSTPROCESSORS' in i.tags}

    if ANNOTATORS_1:
        for anno in ANNOTATORS_1:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(anno, _session, StateManager.add_annotation,
                                             ['POST_ANNOTATORS_1'], previous_services, _agent_gateway, add_bot_to_name)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'POST_ANNOTATORS_1' in i.tags}

    if ANNOTATORS_2:
        for anno in ANNOTATORS_2:
            service, workers, _session, _agent_gateway = \
                make_service_from_config_rec(anno, _session, StateManager.add_annotation,
                                             ['POST_ANNOTATORS_2'], previous_services, _agent_gateway, add_bot_to_name)
            services.append(service)
            worker_tasks.extend(workers)

        previous_services = {i.name for i in services if 'POST_ANNOTATORS_2' in i.tags}

    for anno in ANNOTATORS_3:
        service, workers, _session, _agent_gateway = \
            make_service_from_config_rec(anno, _session, StateManager.add_annotation, ['POST_ANNOTATORS_3'],
                                         previous_services, _agent_gateway, add_bot_to_name)
        services.append(service)
        worker_tasks.extend(workers)

    return services, worker_tasks, _session, _agent_gateway
