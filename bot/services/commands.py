from __future__ import annotations

from typing import Iterable, Sequence

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    MenuButtonCommands,
    MenuButtonWebApp,
    WebAppInfo,
)


DEFAULT_COMMANDS: Sequence[BotCommand] = (
    BotCommand(command="start", description="Запустить бота и открыть меню"),
    BotCommand(command="profile", description="Ваш профиль"),
    BotCommand(command="plan", description="Тариф/план"),
    BotCommand(command="history", description="История операций"),
    BotCommand(command="wallet", description="Кошелёк"),
    BotCommand(command="support", description="Поддержка"),
    BotCommand(command="terms", description="Условия"),
)


async def set_my_commands(
    bot: Bot,
    *,
    commands: Iterable[BotCommand] = DEFAULT_COMMANDS,
    language_code: str = "ru",
) -> None:
    commands_tuple = tuple(commands)
    await bot.set_my_commands(
        commands_tuple,
        scope=BotCommandScopeDefault(),
        language_code=language_code,
    )
    await bot.set_my_commands(
        commands_tuple,
        scope=BotCommandScopeAllPrivateChats(),
        language_code=language_code,
    )


async def set_chat_menu_button(bot: Bot, *, webapp_url: str | None) -> None:
    cleaned = (webapp_url or "").strip()
    if cleaned.lower().startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Открыть приложение", web_app=WebAppInfo(url=cleaned))
        )
        return
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


__all__ = ["set_my_commands", "set_chat_menu_button", "DEFAULT_COMMANDS"]