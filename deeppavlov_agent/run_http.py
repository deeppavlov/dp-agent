import argparse

from aiohttp import web

from .http_api import app_factory
from .settings import PORT


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='port for http client, default 4242', type=int)
    args = parser.parse_args()

    port = args.port or PORT 
    app = app_factory()
    web.run_app(app, port=port)
