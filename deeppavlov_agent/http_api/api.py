import asyncio

import aiohttp_jinja2
import jinja2
from aiohttp import web

from .handlers import ApiHandler, PagesHandler, WSstatsHandler, WSChatHandler


@web.middleware
async def cors_mw(request, handler):
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Max-Age'] = '86400'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['access-control-allow-credentials'] = 'true'
    return resp


async def init_app(agent, session, consumers, logger_stats, output_formatter,
                   debug=False, response_time_limit=0, cors=None):
    middlewares = [cors_mw] if cors else []
    app = web.Application(middlewares=middlewares)
    handler = ApiHandler(output_formatter, response_time_limit)
    pages = PagesHandler(debug)
    stats = WSstatsHandler()
    chat = WSChatHandler(output_formatter)
    consumers = [asyncio.ensure_future(i.call_service(agent.process)) for i in consumers]

    async def on_startup(app):
        app['consumers'] = consumers
        app['agent'] = agent
        app['client_session'] = session
        app['websockets'] = []
        app['logger_stats'] = logger_stats
        asyncio.ensure_future(agent.state_manager.prepare_db())

    async def on_shutdown(app):
        for c in app['consumers']:
            c.cancel()
        if app['client_session']:
            await app['client_session'].close()
        tasks = asyncio.all_tasks()
        for task in tasks:
            task.cancel()

    app.router.add_post('', handler.handle_api_request)
    app.router.add_options('', handler.options)
    app.router.add_get('/api/dialogs/', handler.dialog_list)
    app.router.add_get('/api/dialogs/{dialog_id}', handler.dialog)

    app.router.add_get('/api/user/{user_external_id}', handler.dialogs_by_user)
    app.router.add_get('/ping', pages.ping)
    app.router.add_options('/ping', pages.options)
    app.router.add_get('/debug/current_load', stats.ws_page)
    app.router.add_options('/debug/current_load', stats.options)
    app.router.add_get('/debug/current_load/ws', stats.ws_handler)
    app.router.add_get('/chat', chat.ws_page)
    app.router.add_options('/chat', chat.options)
    app.router.add_get('/chat/ws', chat.ws_handler)
    app.router.add_post('/rating/dialog', handler.dialog_rating)
    app.router.add_options('/rating/dialog', handler.options)
    app.router.add_post('/rating/utterance', handler.utterance_rating)
    app.router.add_options('/rating/utterance', handler.options)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('deeppavlov_agent.http_api', 'templates'))
    return app
