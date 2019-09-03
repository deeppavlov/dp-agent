import asyncio
import logging
import threading
import sys
from multiprocessing import connection, Pipe, Process
from typing import Awaitable, Callable

import telebot

from core.transport.base import ChannelConnectorBase

logger = logging.getLogger('dp_agent_stress_test')
logger.setLevel(logging.INFO)
file_handler = logging.StreamHandler(sys.stderr)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info('begin')

tg_end, connector_end = Pipe()

def worker():
    API_TOKEN = ''
    bot = telebot.TeleBot(API_TOKEN)
    bot.remove_webhook()

    # Handle all other messages with content_type 'text' (content_types defaults to ['text'])
    @bot.message_handler(func=lambda message: True)
    def echo_message(message):
        tg_end.send((message.from_user.id, message.text))

    bot.polling()


class TelegramConnector(ChannelConnectorBase):
    _loop: asyncio.AbstractEventLoop

    def __init__(self, config: dict, on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:
        super(TelegramConnector, self).__init__(config=config, on_channel_callback=on_channel_callback)

        proc = Process(target=worker)
        proc.start()
        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self.send_to_agent())


    async def send_to_channel(self, user_id: str, response: str) -> None:
        print(f'<< {response}')

    async def send_to_agent(self):
        while True:
            user_id, msg = await self._loop.run_in_executor(None, connector_end.recv)
            self._loop.create_task(self._on_channel_callback(utterance=msg,
                                                             channel_id=self._channel_id,
                                                             user_id=str(user_id),
                                                             reset_dialog=False))
