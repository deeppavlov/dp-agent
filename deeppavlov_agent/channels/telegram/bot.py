import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from .utils import MessageResponder

config_dir = Path(__file__).resolve().parent / 'config'

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class DialogState(StatesGroup):
    active = State()
    awaiting_rating = State()
    inactive = State()


def run_tg(token, proxy, agent):
    loop = asyncio.get_event_loop()
    bot = Bot(token=token, loop=loop, proxy=proxy)
    storage = MemoryStorage()  # TODO change to actual storage maybe?
    dp = Dispatcher(bot, storage=storage)
    responder = MessageResponder(
        config_path=config_dir / "telegram_config.yml",
        messages_path=config_dir / "telegram_messages.yml",
        keyboards_path=config_dir / "telegram_keyboards.yml",
    )

    @dp.message_handler(commands="start")
    async def start_handler(message: types.Message):
        text = responder.message("start")
        reply_markup = responder.reply_keyboard("dialog_inactive")

        await message.answer(text, reply_markup=reply_markup)

    @dp.message_handler(commands="help", state="*")
    async def help_handler(message: types.Message):
        text = responder.message("help")

        await message.answer(text)

    @dp.message_handler(commands="complain", state="*")
    async def complain_handler(message: types.Message, state: FSMContext):
        # TODO Add actual complaint logic
        if await state.get_state() == DialogState.active.state:
            text = responder.message("complain_success")
        else:
            text = responder.message("complain_fail")

        await message.answer(text)

    @dp.message_handler(commands="begin", state="*")
    async def begin_dialog(message: types.Message, state: FSMContext):
        state = await state.get_state()
        must_evaluate = (
            state == DialogState.awaiting_rating.state
            and responder.config.evaluation_options.user_must_evaluate
        )
        is_not_finished = state == DialogState.active

        if must_evaluate or is_not_finished:
            text = responder.message("begin_fail")
            reply_markup = None

        else:
            await DialogState.active.set()

            text = responder.message("begin_success")
            reply_markup = responder.reply_keyboard("dialog_active")

        await message.answer(text, reply_markup=reply_markup)

    @dp.message_handler(commands="end", state="*")
    async def end_dialog(message: types.Message, state: FSMContext):
        if await state.get_state() != DialogState.active.state:
            text = responder.message("end_fail")
            reply_markup = responder.reply_keyboard("dialog_inactive")
        else:
            text = responder.message("end_success")
            dialog_id = await agent.state_manager.drop_active_dialog(
                str(message.from_user.id)
            )
            reply_markup = responder.dialog_rating_inline_keyboard(dialog_id)

            await DialogState.awaiting_rating.set()

        await message.answer(text, reply_markup=reply_markup)

    @dp.callback_query_handler(
        lambda c: c.data.startswith("utt"), state=DialogState.active
    )
    async def handle_utterance_rating(
        callback_query: types.CallbackQuery, state: FSMContext
    ):
        _, utterance_id, rating = callback_query.data.split("-")
        await agent.state_manager.set_rating_utterance(
            str(callback_query.from_user.id), utterance_id, rating
        )
        await bot.answer_callback_query(callback_query.id, text=rating.capitalize())

    @dp.callback_query_handler(lambda c: c.data.startswith("dialog"), state="*")
    async def handle_dialog_rating(
        callback_query: types.CallbackQuery, state: FSMContext
    ):
        if await state.get_state() != DialogState.active.state:
            _, dialog_id, rating = callback_query.data.split("-")

            await agent.state_manager.set_rating_dialog(
                str(callback_query.from_user.id), dialog_id, rating
            )

            edited_inline_keyboard = responder.dialog_rating_inline_keyboard(
                dialog_id, chosen_rating=rating
            )

            await bot.edit_message_reply_markup(
                chat_id=callback_query.from_user.id,
                message_id=callback_query.message.message_id,
                reply_markup=edited_inline_keyboard,
            )

            if responder.config.dialog_options.reveal_dialog_id:
                message_text = responder.message(
                    "evaluate_dialog_success_reveal_id", dialog_id=dialog_id
                )
            else:
                message_text = responder.message("evaluate_dialog_success")
            callback_text = "Evaluation saved!"
            reply_markup = responder.reply_keyboard("dialog_inactive")

            await DialogState.inactive.set()

        else:
            callback_text = ""
            message_text = responder.message("evaluate_dialog_success")
            reply_markup = None

        await bot.answer_callback_query(callback_query.id, text=callback_text)
        await bot.send_message(
            callback_query.from_user.id, message_text, reply_markup=reply_markup
        )

    @dp.message_handler(state="*")
    async def handle_message(message: types.Message, state: FSMContext):
        if await state.get_state() == DialogState.active.state:
            response_data = await agent.register_msg(
                utterance=message.text,
                user_external_id=str(message.from_user.id),
                user_device_type="telegram",
                date_time=message.date,
                location="",
                channel_type="telegram",
                require_response=True,
            )
            text = response_data["dialog"].utterances[-1].text
            utterance_id = response_data["dialog"].utterances[-1].utt_id
            reply_markup = responder.utterance_rating_inline_keyboard(utterance_id)
        else:
            text = responder.message("unexpected_message")
            reply_markup = None

        await message.answer(text, reply_markup=reply_markup)

    executor.start_polling(dp, skip_updates=True)
