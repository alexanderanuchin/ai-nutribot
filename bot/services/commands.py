from __future__ import annotations

from typing import Iterable, Sequence

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeDefault


DEFAULT_COMMANDS: Sequence[BotCommand] = (
    BotCommand(command="start", description="Запустить бота и открыть меню"),
    BotCommand(command="profile", description="Ваш профиль"),
    BotCommand(command="plan", description="Тариф/план"),
    BotCommand(command="history", description="История операций"),
    BotCommand(command="wallet", description="Кошелёк"),
    BotCommand(command="terms", description="Условия"),
    BotCommand(command="support", description="Поддержка"),
    BotCommand(command="paysupport", description="Помощь с оплатой"),
    BotCommand(command="cancel", description="Отмена"),
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


__all__ = ["set_my_commands", "DEFAULT_COMMANDS"]