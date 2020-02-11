import asyncio
from typing import Dict, List, Optional
from uuid import uuid4, UUID
from logging import getLogger

from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor

from core.agent import Agent

log = getLogger(__name__)


class ActiveDialog:
    def __init__(self, dialog_id: UUID, skill: str = None) -> None:
        self.id = dialog_id
        self.skill = skill


class TelegramMessageProcessor:
    def __init__(self, agent: Agent, pipeline_data, token, proxy):
        self._agent: Agent = agent
        self._skill_list: List[str] = list(pipeline_data['services']['skills'].keys())
        self._active_dialogs: Dict[int, ActiveDialog] = dict()

        skill_btns = [InlineKeyboardButton(skill, callback_data=skill) for skill in self._skill_list]
        self.skill_kb = InlineKeyboardMarkup(resize_keyboard=True).add(*skill_btns)

        self.begin_end_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('/begin'),
                                                                          KeyboardButton('/end'))

        loop = asyncio.get_event_loop()
        self.bot = Bot(token=token, loop=loop, proxy=proxy)
        dp = Dispatcher(self.bot)

        dp.callback_query_handler()(self.process_callback)
        dp.message_handler(commands=['begin'])(self.handle_begin)
        dp.message_handler(commands=['end'])(self.handle_end)
        dp.message_handler(commands=['start', 'help'])(self.handle_help)
        dp.message_handler()(self.handle_message)

        executor.start_polling(dp, skip_updates=True)

    async def process_callback(self, callback_query: CallbackQuery):
        user_tg_id, skill_name = callback_query.from_user.id, callback_query.data
        if user_tg_id in self._active_dialogs:
            dialog = await self._agent.state_manager.get_or_create_dialog_by_tg_id(self._active_dialogs[user_tg_id].id, 'telegram')
            if not dialog.utterances and self._active_dialogs[user_tg_id].skill:
                await self.bot.answer_callback_query(callback_query.id)
                await self.bot.send_message(user_tg_id,
                                            'Please, send at least one message before switching active skill.')
                return
            dialog.human.attributes['active_skill'] = skill_name
            await self._agent.state_manager.save_dialog(dialog, {}, '')
            self._active_dialogs[user_tg_id].skill = skill_name
            await self.bot.answer_callback_query(callback_query.id)
            await self.bot.send_message(user_tg_id, f'Selected {skill_name} skill.')
            log.info(f'{user_tg_id} selected {skill_name} skill')
        else:
            await self.bot.answer_callback_query(callback_query.id)
            await self.bot.send_message(user_tg_id, 'You are not in a dialog right now. Send /begin to start dialog.')

    async def handle_message(self, message):
        user_tg_id = message.from_user.id
        dialog: Optional[ActiveDialog] = self._active_dialogs.get(user_tg_id)

        if dialog and dialog.skill:
            response = await self._agent.register_msg(
                utterance=message.text,
                user_telegram_id=dialog.id,
                user_device_type='telegram',
                date_time=message.date, location='', channel_type='telegram',
                require_response=True
            )
            await message.answer(response['dialog'].utterances[-1].text)
        else:
            await message.answer('This is Agent skill selection telegram API. Send /begin to start dialog.',
                                 reply_markup=self.begin_end_kb)

    async def handle_begin(self, message):
        user_tg_id = message.from_user.id
        if user_tg_id in self._active_dialogs:
            await message.answer(f'You are already in dialog with `{self._active_dialogs[user_tg_id].skill}` skill. '
                                 'Enter /end command to finish this dialog.')
        else:
            secret_id = uuid4()
            self._active_dialogs[user_tg_id] = ActiveDialog(secret_id)
            await message.answer('Dialog with Agent is started. Select skill to activate. To finish dialog send /end.',
                                 reply_markup=self.skill_kb)
            log.info(f'user {user_tg_id} started dialog with ID {secret_id}')

    async def handle_end(self, message):
        user_tg_id = message.from_user.id
        if user_tg_id in self._active_dialogs:
            params = self._active_dialogs.pop(user_tg_id)
            await message.answer(f'Your dialog with {params.skill} skill is finished. Dialog ID is {params.id}.')
            log.info(f'user {user_tg_id} finished dialog with ID {params.id}')
        else:
            await message.answer('You are not in a dialog right now. Send /begin to start dialog.')

    async def handle_help(self, message) -> None:
        await message.answer('This is Agent skill selection telegram API. Send /begin to start dialog.',
                             reply_markup=self.begin_end_kb)


def run_tg(token, proxy, agent, pipeline_data) -> None:
    tg_msg_processor = TelegramMessageProcessor(agent, pipeline_data, token, proxy)
