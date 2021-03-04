import argparse
import os
from logging import getLogger

import sentry_sdk
from aiohttp import web

from .http_api import app_factory
from .settings import PORT


logger = getLogger(__name__)
sentry_sdk.init(os.getenv('DP_AGENT_SENTRY_DSN'))


def run_http(port, pipeline_configs=None, debug=None, time_limit=None, cors=None, uib_login=None, uib_password=None):
    try:
        app = app_factory(pipeline_configs=pipeline_configs, debug=debug, response_time_limit=time_limit, cors=cors,
                          uib_login=uib_login, uib_password=uib_password)
        web.run_app(app, port=port)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help=f'port for http client, default {PORT}', type=int)
    parser.add_argument('-pl', '--pipeline_configs', help='Pipeline config (overwrite value, defined in settings)',
                        type=str, action='append')
    parser.add_argument('-d', '--debug', help='run in debug mode', action='store_true')
    parser.add_argument('-tl', '--time_limit', help='response time limit, 0 = no limit', type=int)
    args = parser.parse_args()

    port = args.port or PORT
    run_http(port, args.pipeline_configs, args.debug, args.time_limit)
