from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from services.backend import BackendClient

router = Router()

@router.callback_query(F.data == "wizard:start")
async def wizard_start(cb: CallbackQuery):
    await cb.message.answer("Ок, заполним профиль. Напиши свой целевой дневной бюджет в ₽ (число).")
    await cb.answer()

@router.message(F.text.regexp(r"^\d{2,6}$"))
async def wizard_budget(message: Message, store: BackendClient):
    # здесь можно стукнуться в бэк, пока просто подтверждаем
    await message.answer(f"Принял бюджет: {message.text} ₽. Позже добавим сохранение в кабинет 👍")
