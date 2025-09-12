from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(CommandStart())
async def start(msg: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Заполнить анкету", callback_data="wizard:start")
    kb.button(text="Сгенерировать меню", callback_data="menu:gen")
    kb.adjust(1)
    await msg.answer(
        "Привет! Я NutriBot. Составлю персональное меню из блюд ресторанов/магазинов вашего города.",
        reply_markup=kb.as_markup()
    )
