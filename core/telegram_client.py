import asyncio

from uuid import uuid4
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor


class TelegramMessageProcessor:
    def __init__(self, agent, pipeline_data):
        self._agent = agent
        self._skill_list = list(pipeline_data['services']['skills'].keys())
        self._active_dialogs = dict()

    async def handle_message(self, message):
        if message.from_user.id not in self._active_dialogs:
            await message.answer('You are not in dialog with skill right now. To activate skill enter `/begin skill_name` '
                                 f'with skill_name from the following list: {", ".join(self._skill_list)}')
        else:
            response = await self._agent.register_msg(
                utterance=message.text,
                user_telegram_id=self._active_dialogs[message.from_user.id]['id'],
                user_device_type='telegram',
                date_time=message.date, location='', channel_type='telegram',
                require_response=True
            )
            await message.answer(response['dialog'].utterances[-1].text)

    async def handle_begin(self, message):
        args = message.get_args()
        if not args:
            await message.answer('To activate skill enter `/begin skill_name` with skill_name from the following list: '
                                 f'{", ".join(self._skill_list)}')
        elif args not in self._skill_list:
            await message.answer(f'There is no skill `{args}` in the skill list: {", ".join(self._skill_list)}')
        elif message.from_user.id in self._active_dialogs:
            await message.answer(f'You are already in dialog with `{self._active_dialogs[message.from_user.id]["skill"]}` skill. '
                                 'Enter /end command to finish this dialog before starting new.')
        else:
            secret_id = uuid4()
            self._active_dialogs[message.from_user.id] = {'skill': args, 'id': secret_id}
            dialog = await self._agent.state_manager.get_or_create_dialog_by_tg_id(secret_id, 'telegram')
            dialog.human.attributes['active_skill'] = args
            await self._agent.state_manager.save_dialog(dialog, {}, '')
            await message.answer(f'From now on, you are communicating with `{args}` skill.')

    async def handle_end(self, message):
        if message.from_user.id in self._active_dialogs:
            params = self._active_dialogs.pop(message.from_user.id)
            await message.answer(f'You finished dialog with `{params["skill"]}` skill. Dialog ID is `{params["id"]}`.')
        else:
            await message.answer('You are not in dialog with skill right now. To activate skill enter `/begin skill_name` '
                                 f'with skill_name from the following list: {", ".join(self._skill_list)}')

    async def handle_help(self, message):
        await message.answer('This is Agent single skill telegram API.'
                             'You are not in dialog with skill right now. To activate skill enter `/begin skill_name` '
                             f'with skill_name from the following list: {", ".join(self._skill_list)}')


def run_tg(token, proxy, agent, pipeline_data):
    loop = asyncio.get_event_loop()
    bot = Bot(token=token, loop=loop, proxy=proxy)
    dp = Dispatcher(bot)
    tg_msg_processor = TelegramMessageProcessor(agent, pipeline_data)

    dp.message_handler(commands=['begin'])(tg_msg_processor.handle_begin)
    dp.message_handler(commands=['end'])(tg_msg_processor.handle_end)
    dp.message_handler(commands=['start', 'help'])(tg_msg_processor.handle_help)
    dp.message_handler()(tg_msg_processor.handle_message)

    executor.start_polling(dp, skip_updates=True)
