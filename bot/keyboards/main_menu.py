from __future__ import annotations

from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MainMenuAction(str, Enum):
    PROFILE = "profile"
    WALLET = "wallet"
    INFO = "info"


class MainMenuCallback(CallbackData, prefix="main"):
    action: MainMenuAction


def build_main_menu_keyboard(
    *,
    webapp_url: str | None,
    browser_url: str | None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url:
        builder.button(text="Открыть приложение", web_app=WebAppInfo(url=webapp_url))
    elif browser_url:
        builder.button(text="Открыть приложение", url=browser_url)
    else:
        builder.button(
            text="Открыть приложение",
            callback_data=MainMenuCallback(action=MainMenuAction.INFO).pack(),
        )
    builder.button(
        text="👤 Профиль",
        callback_data=MainMenuCallback(action=MainMenuAction.PROFILE).pack(),
    )
    builder.button(
        text="👛 Кошелёк",
        callback_data=MainMenuCallback(action=MainMenuAction.WALLET).pack(),
    )
    builder.button(
        text="ℹ️ Info & Legal",
        callback_data=MainMenuCallback(action=MainMenuAction.INFO).pack(),
    )

    builder.adjust(2, 2)
    return builder.as_markup()


__all__ = [
    "MainMenuAction",
    "MainMenuCallback",
    "build_main_menu_keyboard",
]
