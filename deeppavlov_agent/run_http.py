from aiohttp import web

from .http_api import app_factory
from .base_settings import PORT

if __name__ == '__main__':
    app = app_factory()
    web.run_app(app, port=PORT)
