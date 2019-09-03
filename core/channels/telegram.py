import asyncio
import threading
from logging import getLogger
from multiprocessing import connection, Pipe, Process
from typing import Awaitable, Callable

import telebot

from core.transport.base import ChannelConnectorBase

logger = getLogger(__name__)
# TODO: move api token to config
API_TOKEN = ''


def tg_bot(child_conn: connection.Connection) -> None:
    """Initiates Telegram bot and starts message polling from Telegram and TelegramConnector."""
    bot = telebot.TeleBot(API_TOKEN)
    bot.remove_webhook()

    @bot.message_handler(func=lambda message: True)
    def send_to_tg_connector(message: telebot.types.Message) -> None:
        """Extracts user_id and text from message and sends them to the TelegramConnector through Pipe."""
        child_conn.send((message.from_user.id, message.text))

    def poll_channel() -> None:
        """Awaits response from agent and sends it to user."""
        while True:
            user_id, msg = child_conn.recv()
            bot.send_message(int(user_id), msg)

    channel_poller = threading.Thread(target=poll_channel)
    channel_poller.start()
    bot.polling()


class TelegramConnector(ChannelConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _parent_conn: connection.Connection

    def __init__(self, config: dict, on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:
        """Launches Telegram bot in a separate process, starts Pipe polling to send utterances to Agent."""
        super(TelegramConnector, self).__init__(config=config, on_channel_callback=on_channel_callback)
        self._parent_conn, child_conn = Pipe()

        telegram_bot_proc = Process(target=tg_bot, args=(child_conn,))
        telegram_bot_proc.start()
        logger.info('Telegram bot is launched')

        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self.send_to_agent())

    async def send_to_channel(self, user_id: str, response: str) -> None:
        """Receives `user_id` and `response` to utterance from Agent and sends them to Telegram Bot through Pipe."""
        self._parent_conn.send((user_id, response))

    async def send_to_agent(self) -> None:
        """Awaits user_id and utterance from Telegram bot and sends them to Agent through _on_channel_callback."""
        while True:
            user_id, utterance = await self._loop.run_in_executor(None, self._parent_conn.recv)
            self._loop.create_task(self._on_channel_callback(utterance=utterance,
                                                             channel_id=self._channel_id,
                                                             user_id=str(user_id),
                                                             reset_dialog=False))
