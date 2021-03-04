import asyncio
import urllib.request
from datetime import datetime
from string import hexdigits
from time import time

import aiohttp
import aiohttp_jinja2
from aiohttp import web


async def handle_command(payload, user_id, state_manager):
    if payload in {'/start', '/close'} and state_manager:
        await state_manager.drop_active_dialog(user_id)
        return True


class ApiHandler:
    def __init__(self, output_formatter, response_time_limit=5, uib_login=None, uib_password=None):
        self.output_formatter = output_formatter
        self.response_time_limit = response_time_limit
        self.uib_auth = self.init_uib(uib_login, uib_password)

    @staticmethod
    def init_uib(uib_login, uib_password):
        if uib_login is not None and uib_password is not None:
            return aiohttp.BasicAuth(uib_login, uib_password)
        return None

    async def handle_api_request(self, request):
        response = {}
        register_msg = request.app['agent'].register_msg
        if request.method == 'POST':
            if 'content-type' not in request.headers \
                    or not request.headers['content-type'].startswith('application/json'):
                raise web.HTTPBadRequest(reason='Content-Type should be application/json')
            data = await request.json()

            user_id = data.pop('user_id')
            payload = data.pop('payload', '')

            deadline_timestamp = None
            if self.response_time_limit:
                deadline_timestamp = time() + self.response_time_limit

            if not user_id:
                raise web.HTTPBadRequest(reason='user_id key is required')

            command_performed = await handle_command(payload, user_id, request.app['agent'].state_manager)
            if command_performed:
                return web.json_response({})

            response = await asyncio.shield(
                register_msg(utterance=payload, user_external_id=user_id,
                             user_device_type=data.pop('user_device_type', 'http'),
                             date_time=datetime.now(),
                             location=data.pop('location', ''),
                             channel_type='http_client',
                             message_attrs=data, require_response=True,
                             deadline_timestamp=deadline_timestamp)
            )

            if response is None:
                raise RuntimeError('Got None instead of a bot response.')

            return web.json_response(self.output_formatter(response['dialog'].to_dict()))

    async def handle_uib_request(self, request):
        register_msg = request.app['agent'].register_msg
        if request.method == 'POST':
            if 'content-type' not in request.headers \
                    or not request.headers['content-type'].startswith('application/json'):
                raise web.HTTPBadRequest(reason='Content-Type should be application/json')
            if self.uib_auth is None:
                raise web.HTTPBadRequest(reason='The Unified Inbox credentials were not initialized')
            data = await request.json()
            if data['data']['attachmenttype'] != 'text':
                return web.json_response({'status': 200, 'info': 'OK'})

            user_id = data['data']['receiveraddress']
            payload = data['data']['messagepreview']
            connectionname = data['data']['connectionname']

            deadline_timestamp = None
            if self.response_time_limit:
                deadline_timestamp = time() + self.response_time_limit

            response = await asyncio.shield(
                register_msg(utterance=payload, user_external_id=user_id,
                             user_device_type='uib',
                             date_time=datetime.now(),
                             location='',
                             channel_type='http_client',
                             require_response=True,
                             deadline_timestamp=deadline_timestamp)
            )

            if response is None:
                raise RuntimeError('Got None instead of a bot response.')

            resp_payload = response['dialog'].to_dict()
            response = {
                'message': {
                    'receivers': [{'name': 'name', 'address': user_id, 'Connector': connectionname, 'type': ''}],
                    'parts': [{'id': '1', 'contentType': 'text/plain', 'data': resp_payload['utterances'][-1]['text'],
                              'size': len(resp_payload['utterances'][-1]['text']), 'type': 'body', 'sort': 0}]
                }
            }
            async with aiohttp.ClientSession() as session:
                resp = await session.post(f"https://apiv2.unificationengine.com/v2/message/send",
                                          auth=self.uib_auth,
                                          json=response)
            return web.json_response({'status': resp.status, 'info': 'OK'})

    async def dialog(self, request):
        state_manager = request.app['agent'].state_manager
        dialog_id = request.match_info['dialog_id']
        if all(c in hexdigits for c in dialog_id):
            if len(dialog_id) == 24:
                dialog_obj = await state_manager.get_dialog_by_id(dialog_id)
            else:
                dialog_obj = await state_manager.get_dialog_by_dialog_id(dialog_id)

            if not dialog_obj:
                raise web.HTTPNotFound(reason=f'dialog with id {dialog_id} does not exist')

            return web.json_response(dialog_obj.to_dict())

        raise web.HTTPBadRequest(
            reason='dialog id should be 24-character hex string or 34-char hex string for dialog_id')

    async def dialog_list(self, request):
        """Function to get list of dialog ids as JSON response"""
        state_manager = request.app['agent'].state_manager

        params = {
            'offset': int(request.rel_url.query.get('offset', 0)),
            'limit': int(request.rel_url.query.get('limit', 100)),
        }
        _active_raw = request.rel_url.query.get('_active', None)
        if _active_raw:
            active = bool(int(_active_raw))
            params["_active"] = active

        list_ids = await state_manager.list_dialog_ids(**params)

        if len(list_ids) < params['limit']:
            # final page or no more items?
            next_offset_link = None
        else:
            params['offset'] = params['offset']+params['limit']
            next_offset_link = "?"+urllib.parse.urlencode(params)

        resp_dict = {
            "dialog_ids": list_ids,
            "next": next_offset_link
        }
        return web.json_response(resp_dict)

    async def dialogs_by_user(self, request):
        state_manager = request.app['agent'].state_manager
        user_external_id = request.match_info['user_external_id']
        dialogs = await state_manager.get_dialogs_by_user_ext_id(user_external_id)
        return web.json_response([i.to_dict() for i in dialogs])

    async def dialog_rating(self, request):
        state_manager = request.app['agent'].state_manager
        data = await request.json()
        dialog_id = data.pop('dialog_id')
        user_id = data.pop('user_id', None)
        rating = data.pop('rating')
        await state_manager.set_rating_dialog(user_id, dialog_id, rating)
        return web.Response()

    async def utterance_rating(self, request):
        state_manager = request.app['agent'].state_manager
        data = await request.json()
        user_id = data.pop('user_id', None)
        rating = data.pop('rating')
        utt_id = data.pop('utt_id')
        await state_manager.set_rating_utterance(user_id, utt_id, rating)
        return web.Response()

    async def options(self, request):
        return web.Response(headers={'Access-Control-Allow-Methods': 'POST, OPTIONS'})


class PagesHandler:
    def __init__(self, debug=False):
        self.debug = debug

    async def ping(self, request):
        return web.json_response("pong")

    async def options(self, request):
        return web.Response(headers={'Access-Control-Allow-Methods': 'GET, OPTIONS'})


class WSstatsHandler:
    def __init__(self):
        self.update_time = 0.5

    @aiohttp_jinja2.template('services_ws_highcharts.html')
    async def ws_page(self, request):
        return {}

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        request.app['websockets'].append(ws)
        logger_stats = request.app['logger_stats']
        while True:
            data = dict(logger_stats.get_current_load())
            await ws.send_json(data)
            await asyncio.sleep(self.update_time)

        return ws

    async def options(self, request):
        return web.Response(headers={'Access-Control-Allow-Methods': 'GET, OPTIONS'})


class WSChatHandler:
    def __init__(self, output_formatter):
        self.output_formatter = output_formatter

    @aiohttp_jinja2.template('chat.html')
    async def ws_page(self, request):
        return {}

    async def ws_handler(self, request):
        register_msg = request.app['agent'].register_msg
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        while True:
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.text:
                data = msg.json()
                user_id = data.pop('user_id')
                payload = data.pop('payload', '')
                deadline_timestamp = None
                if not user_id:
                    raise web.HTTPBadRequest(reason='user_id key is required')
                command_performed = await handle_command(payload, user_id, request.app['agent'].state_manager)
                if command_performed:
                    await ws.send_json('command_performed')
                    continue

                response = await register_msg(
                    utterance=payload, user_external_id=user_id,
                    user_device_type=data.pop('user_device_type', 'websocket'),
                    date_time=datetime.now(),
                    location=data.pop('location', ''),
                    channel_type='ws_client',
                    message_attrs=data, require_response=True,
                    deadline_timestamp=deadline_timestamp
                )
                if response is None:
                    raise RuntimeError('Got None instead of a bot response.')
                await ws.send_json(self.output_formatter(response['dialog'].to_dict()))
            else:
                await ws.close()
                break

        return ws

    async def options(self, request):
        return web.Response(headers={'Access-Control-Allow-Methods': 'GET, OPTIONS'})
