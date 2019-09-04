import asyncio
from logging import getLogger
from typing import Awaitable, Callable, Match

from aiotg import Bot, Chat

from core.transport.base import ChannelConnectorBase

logger = getLogger(__name__)


class TelegramConnector(ChannelConnectorBase):
    _loop: asyncio.AbstractEventLoop
    _bot: Bot

    def __init__(self, config: dict, on_channel_callback: Callable[[str, str, str, bool], Awaitable]) -> None:
        """Adds Telegram bot poller task to the event loop, initiates user messages handler."""
        super(TelegramConnector, self).__init__(config=config, on_channel_callback=on_channel_callback)
        self._loop = asyncio.get_event_loop()

        api_token = config['channel'].get('api_token')
        if not api_token:
            raise ValueError('Wrong API token for telegram bot')

        self._bot = Bot(api_token)

        @self._bot.command(r'.+')
        async def send_to_agent(chat: Chat, match: Match) -> None:
            self._loop.create_task(self._on_channel_callback(utterance=chat.message['text'],
                                                             channel_id=self._channel_id,
                                                             user_id=str(chat.sender['id']),
                                                             reset_dialog=False))

        self._loop.create_task(self._bot.loop())
        logger.info('Telegram bot is launched')

    async def send_to_channel(self, user_id: str, response: str) -> None:
        self._bot.send_message(int(user_id), response)
