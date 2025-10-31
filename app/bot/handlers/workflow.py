import os

import aiohttp
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.keyboards import create_city_kb
from bot.states.add_item import AddItem

router = Router()


@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.answer(
        "Привет, это бот, который поможет тебе найти потерянную вещь.\nДля начала введи свой город",
        # reply_markup=create_city_kb(),
    )
    await state.set_state(AddItem.city)


@router.message(AddItem.city, F.location)
@router.message(AddItem.city, F.text)
async def save_city(message: types.Message, state: FSMContext):
    city = message.text
    await state.set_data({"city": city})
    await message.answer("Теперь введи описание потерянной вещи")
    await state.set_state(AddItem.description)


@router.message(AddItem.description)
async def save_description(message: types.Message, state: FSMContext):
    description = message.text
    await state.update_data(description=description)
    await message.answer(
        "Сколько наиболее релевантных ответов тебе необходимо прислать?"
    )
    await state.set_state(AddItem.k_top)


@router.message(AddItem.k_top)
async def save_k_top(message: types.Message, state: FSMContext):
    try:
        k_top = int(message.text)
    except ValueError:
        return await message.answer("Введи пожалуйста числом")

    state_data = await state.get_data()
    state_data.update({"k_top": k_top})
    print(state_data)

    async with aiohttp.ClientSession() as session:
        async with session.get(os.environ.get("API_URL") + "/set") as response:
            print(response.status, await response.text())
