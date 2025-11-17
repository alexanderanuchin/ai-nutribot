from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_auth_bridge_url(webapp_url: str | None) -> str | None:
    cleaned = (webapp_url or "").strip().rstrip("/")
    if not cleaned:
        return None
    return f"{cleaned}/auth-bridge"


def build_authorize_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sanitized_url = build_auth_bridge_url(webapp_url)
    if sanitized_url and sanitized_url.lower().startswith("https://"):
        builder.button(text="Авторизоваться", web_app=WebAppInfo(url=sanitized_url))
    elif sanitized_url:
        builder.button(text="Авторизоваться", url=sanitized_url)
    builder.adjust(1)
    return builder.as_markup()
