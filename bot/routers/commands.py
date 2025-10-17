from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.backend_client import BackendAuthError, BackendClient, BackendError
from bot.keyboards.inline import (
    build_quick_actions_keyboard,
    create_crm_entry_point,
)
from bot.keyboards.main_menu import build_main_menu_keyboard
from bot.logging_utils import get_request_id
from bot.utils.texts import CANCELLED_TEXT, MAIN_SCREEN_TEXT

logger = logging.getLogger("bot.commands")

router = Router(name="commands")


async def process_start(
    message: Message,
    backend: BackendClient,
    access_token: str | None,
    webapp_url: str,
    bot_username: str,
    request_id: str | None = None,
) -> None:
    extra: str
    if access_token:
        try:
            await backend.get_me(access_token)
            extra = "\n\nВы авторизованы — можно сразу перейти к действиям из меню."
        except BackendAuthError:
            extra = "\n\nСессия истекла. Откройте CRM или заполните профиль заново."
        except BackendError as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "start profile_fetch_failed",
                extra={
                    "rid": request_id or get_request_id(),
                    "error": str(exc),
                },
            )
            extra = "\n\nНе удалось проверить профиль — используйте меню ниже."
        except Exception as exc:  # pragma: no cover - неожиданные ошибки
            logger.exception(
                "start unexpected_error",
                extra={"rid": request_id or get_request_id(), "error": str(exc)},
            )
            extra = "\n\nВоспользуйтесь меню ниже для продолжения."
    else:
        extra = "\n\nЧтобы начать, авторизуйтесь через CRM Mini App."

    await message.answer(
        MAIN_SCREEN_TEXT + extra,
        reply_markup=build_main_menu_keyboard(),
    )

    crm_entry = create_crm_entry_point(webapp_url=webapp_url, bot_username=bot_username)
    quick_actions_markup = build_quick_actions_keyboard(crm_entry=crm_entry)
    await message.answer("Быстрые действия:", reply_markup=quick_actions_markup)


async def process_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        CANCELLED_TEXT,
        reply_markup=build_main_menu_keyboard(),
    )


@router.message(CommandStart())
async def on_start_command(
    message: Message,
    backend: BackendClient,
    access_token: str | None,
    webapp_url: str,
    bot_username: str,
    request_id: str | None,
) -> None:
    await process_start(
        message,
        backend,
        access_token,
        webapp_url,
        bot_username,
        request_id,
    )


@router.message(Command("cancel"))
async def on_cancel_command(message: Message, state: FSMContext) -> None:
    await process_cancel(message, state)


@router.message(Command("cansel"))
async def on_cansel_alias(message: Message, state: FSMContext) -> None:
    await process_cancel(message, state)


@router.message(F.text == "✖️ Отмена")
async def on_cancel_button(message: Message, state: FSMContext) -> None:
    await process_cancel(message, state)


__all__ = ["router", "process_start", "process_cancel"]