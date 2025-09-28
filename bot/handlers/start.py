from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..backend_client import BackendAuthError, BackendClient, BackendError

router = Router()

@router.message(CommandStart())
async def start(
    msg: Message,
    backend: BackendClient,
    access_token: str | None,
    webapp_url: str,
):
    greeting = (
        "Привет! Я NutriBot и помогу составить персональное меню.\n"
        "Используй команду /profile, чтобы обновить анкету, и /cancel для отмены шагов."
    )

    if access_token:
        try:
            await backend.get_me(access_token)
            extra = "Готов обновить ваш профиль — нажмите кнопку ниже."
        except BackendAuthError:
            extra = "Требуется переавторизация через WebApp."
        except BackendError:
            extra = "Не удалось получить профиль, но вы можете попробовать заполнить анкету."
    else:
        extra = "Чтобы начать, авторизуйтесь через WebApp и затем заполните анкету."

    kb = InlineKeyboardBuilder()
    kb.button(text="Заполнить анкету", callback_data="wizard:start")
    if webapp_url:
        if webapp_url.lower().startswith("https://"):
            kb.button(text="Открыть WebApp", web_app=WebAppInfo(url=webapp_url))
        else:
            kb.button(text="Открыть WebApp", url=webapp_url)
    kb.button(text="Сгенерировать меню", callback_data="menu:gen")
    kb.adjust(1)
    await msg.answer(f"{greeting}\n\n{extra}", reply_markup=kb.as_markup())
