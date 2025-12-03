import aiohttp
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from db import City, User

router = Router()


class ChangeSettings(StatesGroup):
    city_id = State()
    top_k = State()


class ChangeSettings(StatesGroup):
    city = State()
    top_k = State()


# Helper function
def cities_keyboard(session: Session):
    cities = session.query(City).all()
    keyboard = []
    for city in cities:
        keyboard.append(
            [InlineKeyboardButton(text=city.name, callback_data=f"city_{city.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def top_k_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(k), callback_data=f"topk_{k}")
                for k in [3, 5, 10]
            ]
        ]
    )


@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext, session: Session):
    await message.answer(
        "Привет, это бот, который поможет тебе найти потерянную вещь.\nДля начала введи свой город",
        reply_markup=cities_keyboard(session),
    )
    await state.set_state(ChangeSettings.city)


@router.callback_query(F.data.startswith("city_"))
async def process_city(callback: types.CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[1])
    await state.update_data(city_id=city_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(k), callback_data=f"topk_{k}")
                for k in [3, 5, 10]
            ]
        ]
    )
    await callback.message.edit_text(
        "Сколько релевантных ответов тебе находить?", reply_markup=keyboard
    )
    await state.set_state(ChangeSettings.top_k)


@router.callback_query(F.data.startswith("topk_"))
async def process_topk(
    callback: types.CallbackQuery, state: FSMContext, session: Session
):
    top_k = int(callback.data.split("_")[1])
    data = await state.get_data()

    # Save/update user
    user = session.query(User).filter(User.id == callback.from_user.id).first()
    if not user:
        user = User(id=callback.from_user.id, first_name=callback.from_user.first_name)
        session.add(user)
    if "city_id" in data:
        user.city_id = data["city_id"]
    user.top_k = top_k
    session.commit()

    await callback.message.edit_text(
        f"Настройки сохранены!\nГород: {user.city.name}\nСколько выдавать: {top_k}"
    )
    await state.clear()


@router.message(Command("settings"))
async def start(message: types.Message, state: FSMContext, session: Session):
    user = session.query(User).filter(User.id == message.from_user.id).first()
    if not user:
        await message.answer("Please run /start first")
        return
    await message.answer(
        f"Настройки\n---\nГород: {user.city.name}\nСколько выдавать: {user.top_k}"
    )
    await state.clear()


# Separate commands
@router.message(Command("city"))
async def change_city(message: types.Message, state: FSMContext, session: Session):
    await message.answer("Выбери другой город:", reply_markup=cities_keyboard(session))
    await state.set_state(ChangeSettings.city)


@router.message(Command("top_k"))
async def change_topk(message: types.Message, state: FSMContext):
    keyboard = top_k_keyboard()
    await message.answer(
        "Сколько релевантных ответов тебе находить?", reply_markup=keyboard
    )
    await state.set_state(ChangeSettings.top_k)
