from aiogram.fsm.state import StatesGroup, State


class AddItem(StatesGroup):
    city = State()
    description = State()
    k_top = State()
