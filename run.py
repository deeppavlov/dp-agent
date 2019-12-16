import argparse
import asyncio
import json
import logging

import yaml
from aiohttp import web

from core.agent import Agent
from core.cmd_client import run_cmd
from core.connectors import EventSetOutputConnector
from core.db import DataBase
from core.http_api import init_app
from core.pipeline import Pipeline
from core.service import Service
from core.state_manager import StateManager
from core.workflow_manager import WorkflowManager
from parse_config import parse_pipeline_config

service_logger = logging.getLogger('service_logger')

parser = argparse.ArgumentParser()
parser.add_argument('-pl', '--pipeline_config', help='service name for service run mode', type=str, default='pipeline_conf.json')
parser.add_argument('-db', '--db_config', help='service name for service run mode', type=str, default='db_conf.json')
parser.add_argument("-ch", "--channel", help="run agent in telegram, cmd_client or http_client", type=str,
                    choices=['cmd_client', 'http_client', 'telegram'], default='cmd_client')
parser.add_argument('-p', '--port', help='port for http client, default 4242', default=4242)
parser.add_argument("-px", "--proxy", help="proxy for telegram client", type=str, default='')
parser.add_argument('-t', '--token', help='token for telegram client', type=str)

parser.add_argument('-rl', '--response_logger', help='run agent with services response logging', action='store_true')
parser.add_argument('-d', '--debug', help='run in debug mode', action='store_true')
args = parser.parse_args()


def main():
    with open(args.db_config, 'r') as db_config:
        if args.db_config.endswith('.json'):
            db_data = json.load(db_config)
        elif args.db_config.endswith('.yml'):
            db_data = yaml.load(db_config)
        else:
            raise ValueError('unknown format for db_config')
    db = DataBase(**db_data)

    sm = StateManager(db.get_db())

    with open(args.pipeline_config, 'r') as pipeline_config:
        if args.pipeline_config.endswith('.json'):
            pipeline_data = json.load(pipeline_config)
        elif args.pipeline_config.endswith('.yml'):
            pipeline_data = yaml.load(pipeline_config)
        else:
            raise ValueError('unknown format for pipeline_config')
    services, workers, session, gateway = parse_pipeline_config(pipeline_data, sm, None)

    input_srv = Service('input', None, sm.add_human_utterance, 1, ['input'])
    endpoint_srv = Service('responder', EventSetOutputConnector('responder').send,
                        sm.save_dialog, 1, ['responder'])

    pipeline = Pipeline(services)
    pipeline.add_responder_service(endpoint_srv)
    pipeline.add_input_service(input_srv)

    agent = Agent(pipeline, sm, WorkflowManager(), use_response_logger=args.response_logger)
    if gateway:
        gateway.on_channel_callback = agent.register_msg
        gateway.on_service_callback = agent.process

    if args.channel == 'cmd_client':

        loop = asyncio.get_event_loop()
        loop.set_debug(args.debug)
        future = asyncio.ensure_future(run_cmd(agent.register_msg))
        for i in workers:
            loop.create_task(i.call_service(agent.process))
        try:
            loop.run_until_complete(future)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise e
        finally:
            future.cancel()
            if session:
                loop.run_until_complete(session.close())
            if gateway:
                gateway.disconnect()
            loop.stop()
            loop.close()
            logging.shutdown()
    elif args.channel == 'http_client':
        app = init_app(agent, session, workers, args.debug)
        web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
