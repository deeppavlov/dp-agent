from pathlib import Path
from string import Template
from typing import Union

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from pydantic import BaseModel
from yaml import load
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def _load_yml(path):
    with open(path, "r") as yml_f:
        data = load(yml_f, Loader=Loader)
    return data


class YmlModel(BaseModel):
    @classmethod
    def from_yml(cls, path):
        return cls.parse_obj(_load_yml(path))


class DialogOptions(BaseModel):
    reveal_dialog_id: bool


class EvaluationOptions(BaseModel):
    user_must_evaluate: bool
    min_score: int
    max_score: int


class Config(YmlModel):
    dialog_options: DialogOptions
    evaluation_options: EvaluationOptions


class Messages(YmlModel):
    start: str
    help: str
    complain_success: str
    complain_fail: str
    begin_success: str
    begin_fail: str
    end_success: str
    end_fail: str
    evaluate_dialog_success: str
    evaluate_dialog_success_reveal_id: str
    evaluate_dialog_fail: str
    unexpected_message: str


class Keyboards(YmlModel):
    dialog_inactive: list
    dialog_active: list


class MessageResponder:
    def __init__(
        self,
        config_path: Union[Path, str],
        messages_path: Union[Path, str],
        keyboards_path: Union[Path, str],
    ):
        self._config = Config.from_yml(config_path)
        self._messages = Messages.from_yml(messages_path)
        self._keyboards = Keyboards.from_yml(keyboards_path)

    @property
    def config(self) -> Config:
        return self._config

    def message(self, key: str, **kwargs) -> str:
        """Create text from template with substituted placeholders

        Args:
            key: message key
            **kwargs: substitutions if the message is a template

        Returns: string with substituted placeholders

        """
        template = Template(self._messages.dict()[key])
        return template.safe_substitute(**kwargs)

    def dialog_rating_inline_keyboard(
        self, dialog_id: str, chosen_rating: Union[str, int] = None
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard with rating buttons. Min and max score are set via config.
        Provide chosen_rating argument if the keyboard is edited after the conversation was rated

        Args:
            dialog_id: dialog uuid
            chosen_rating: this rating button will be shown with a star in front of the rating value

        Returns: instance of InlineKeyboardMarkup

        """
        reply_markup = InlineKeyboardMarkup(row_width=5)
        min_range = self.config.evaluation_options.min_score
        max_range = self.config.evaluation_options.max_score + 1

        for rating in range(min_range, max_range):
            btn_text = str(rating)
            if chosen_rating:
                if int(chosen_rating) == int(rating):
                    btn_text = f"⭐️{btn_text}"
            btn = InlineKeyboardButton(
                btn_text, callback_data=f"dialog-{dialog_id}-{rating}"
            )
            reply_markup.insert(btn)

        return reply_markup

    def utterance_rating_inline_keyboard(self, utterance_id: str) -> InlineKeyboardMarkup:
        """Create inline keyboard with thumbs up/down buttons

        Args:
            utterance_id: utterance uuid

        Returns: instance of InlineKeyboardMarkup

        """
        reply_markup = InlineKeyboardMarkup(row_width=2)
        reply_markup.insert(
            InlineKeyboardButton("👍", callback_data=f"utt-{utterance_id}-like")
        )
        reply_markup.insert(
            InlineKeyboardButton("👎", callback_data=f"utt-{utterance_id}-dislike")
        )

        return reply_markup

    def reply_keyboard(self, state: str) -> ReplyKeyboardMarkup:
        """Create keyboard with buttons

        Args:
            state: pre-configured keyboard state

        Returns: reply keyboard with pre-configured buttons

        """
        buttons = self._keyboards.dict()[state]
        reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        reply_markup.add(*buttons)

        return reply_markup
