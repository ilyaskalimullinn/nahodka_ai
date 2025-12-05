import os
from pathlib import Path
import aiohttp
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db import City, User, TelegramChannelMessage, TelegramChannelSource
from model import ModelService

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
        f"Настройки сохранены!\nГород: {user.city.name}\nСколько выдавать: {top_k}\nТеперь введи запрос ИЛИ отправь одну фотографию!"
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


@router.message(Command("help"))
async def start(message: types.Message, state: FSMContext, session: Session):
    await message.answer(
        "Привет! Этот бот — помощник в поиске потерянных вещей. Просто отправь описание вещи или ее фотографию (только одно из двух), и мы отправим тебе наиболее подходящие посты"
    )


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


@router.message()
async def answer_question(
    message: types.Message,
    state: FSMContext,
    session: Session,
    model_service: ModelService,
):
    text = message.text
    photo_id = None
    if message.photo is not None and len(message.photo) > 0:
        photo_id = message.photo[-1].file_id

    if (text is None) == (photo_id is None):
        await message.answer(
            "Отправь одно из двух: либо фото, либо текстовое сообщение"
        )
        return

    user = session.query(User).filter(User.id == message.from_user.id).first()
    if user is None:
        await message.answer("Сначала напиши `/start` и выбери настройки!")
        return

    status_msg = await message.answer("Считаю...")
    if text is not None:
        embedding = model_service.encode_text(text)
    elif photo_id is not None:
        save_dir = (
            Path(__file__) / f"../../../assets/photos/__users__/{user.id}"
        ).resolve()
        os.makedirs(save_dir, exist_ok=True)
        photo_path = save_dir / f"{photo_id}.png"
        await message.bot.download(file=photo_id, destination=str(photo_path))

        embedding = model_service.encode_image(photo_path)

    distance_expr = TelegramChannelMessage.embedding.l2_distance(embedding)

    partition_key = func.coalesce(
        TelegramChannelMessage.grouped_id, TelegramChannelMessage.message_id
    )

    ranked_messages_cte = (
        select(
            TelegramChannelMessage,
            distance_expr.label("distance"),
            func.row_number()
            .over(
                partition_by=partition_key,
                order_by=distance_expr,
            )
            .label("rn"),
        )
        .join(TelegramChannelMessage.channel)
        .filter(TelegramChannelSource.city_id == user.city_id)
        .cte("ranked_messages")
    )

    results = (
        select(TelegramChannelMessage)
        .join(
            ranked_messages_cte, TelegramChannelMessage.id == ranked_messages_cte.c.id
        )
        .where(ranked_messages_cte.c.rn == 1)
        .order_by(ranked_messages_cte.c.distance)
        .limit(user.top_k)
    )
    results = session.scalars(results)

    results = list(results)

    if len(results) == 0:
        await status_msg.edit_text("Не нашлось результатов!")
        return

    await status_msg.edit_text("Наиболее релевантные посты:")

    for msg in results:
        await message.bot.forward_message(
            chat_id=message.chat.id,
            from_chat_id=msg.channel_id,
            message_id=msg.message_id,
        )
