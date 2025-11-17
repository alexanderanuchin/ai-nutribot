from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo


def build_auth_bridge_url(webapp_url: str | None) -> str | None:
    cleaned = (webapp_url or "").strip().rstrip("/")
    if not cleaned:
        return None
    return f"{cleaned}/auth-bridge"


def build_authorize_keyboard(webapp_url: str) -> ReplyKeyboardMarkup:
    sanitized_url = build_auth_bridge_url(webapp_url) or ""
    button = KeyboardButton(
        text="Авторизоваться",
        web_app=WebAppInfo(url=sanitized_url) if sanitized_url else None,
    )
    return ReplyKeyboardMarkup(
        keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True, is_persistent=False
    )
