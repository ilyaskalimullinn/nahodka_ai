from aiogram import types
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup


def create_city_kb() -> ReplyKeyboardMarkup:
    keyboard = [[
        types.KeyboardButton(text='Поделиться локацией', request_location=True)
    ]]
    return ReplyKeyboardMarkup(keyboard=keyboard, one_time_keyboard=True)
