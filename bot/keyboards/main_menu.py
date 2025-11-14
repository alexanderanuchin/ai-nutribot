from __future__ import annotations

from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MainMenuAction(str, Enum):
    PROFILE = "profile"
    WALLET = "wallet"
    SUPPORT = "support"
    TERMS = "terms"


class MainMenuCallback(CallbackData, prefix="main"):
    action: MainMenuAction


def build_main_menu_keyboard(
    *,
    webapp_url: str | None,
    browser_url: str | None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    first_row = 0
    if webapp_url:
        builder.button(
            text="Открыть приложение (встроенно)",
            web_app=WebAppInfo(url=webapp_url),
        )
        first_row += 1
    if browser_url:
        # Показываем ссылку в браузер всегда, если есть HTTPS-домен.
        builder.button(text="Открыть в браузере", url=browser_url)
        first_row += 1
    if not first_row and browser_url:
        first_row = 1
    builder.button(
        text="👤 Профиль",
        callback_data=MainMenuCallback(action=MainMenuAction.PROFILE).pack(),
    )
    builder.button(
        text="👛 Кошелёк",
        callback_data=MainMenuCallback(action=MainMenuAction.WALLET).pack(),
    )
    builder.button(
        text="🆘 Поддержка",
        callback_data=MainMenuCallback(action=MainMenuAction.SUPPORT).pack(),
    )
    builder.button(
        text="📄 Условия",
        callback_data=MainMenuCallback(action=MainMenuAction.TERMS).pack(),
    )

    layout: list[int] = []
    if first_row:
        layout.append(first_row)
    layout.extend((2, 2))
    builder.adjust(*layout)
    return builder.as_markup()


__all__ = [
    "MainMenuAction",
    "MainMenuCallback",
    "build_main_menu_keyboard",
]
