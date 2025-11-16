from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo


def build_authorize_keyboard(webapp_url: str) -> ReplyKeyboardMarkup:
    sanitized_url = f"{(webapp_url or '').rstrip('/')}/auth-bridge" if webapp_url else ""
    button = KeyboardButton(
        text="Авторизоваться",
        web_app=WebAppInfo(url=sanitized_url) if sanitized_url else None,
    )
    return ReplyKeyboardMarkup(
        keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True, is_persistent=False
    )
