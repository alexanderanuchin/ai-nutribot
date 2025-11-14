from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.backend_client import BackendAuthError, BackendClient, BackendError
from bot.config import Config
from bot.keyboards.inline import build_quick_actions_keyboard, create_crm_entry_point
from bot.keyboards.main_menu import build_main_menu_keyboard
from bot.logkit import get_request_id
from bot.utils.texts import CANCELLED_TEXT, build_start_message

logger = logging.getLogger("bot.commands")

router = Router(name="commands")


async def process_start(
    message: Message,
    backend: BackendClient,
    access_token: str | None,
    config: Config,
    *,
    request_id: str | None = None,
    experimental_menu: bool = False,
) -> None:
    rid = request_id or get_request_id()
    authorized = False
    status_note: str | None = None
    if access_token:
        try:
            await backend.get_me(access_token)
            authorized = True
        except BackendAuthError:
            status_note = "Сессия истекла. Откройте мини-приложение и войдите заново."
        except BackendError as exc:  # pragma: no cover - сетевые ошибки
            logger.warning(
                "start profile_fetch_failed",
                extra={"rid": rid, "error": str(exc)},
            )
            status_note = "Не удалось проверить профиль — используйте меню ниже."
        except Exception as exc:  # pragma: no cover - неожиданные ошибки
            logger.exception(
                "start unexpected_error",
                extra={"rid": rid, "error": str(exc)},
            )
            status_note = "Воспользуйтесь кнопками ниже для продолжения."
    text = build_start_message(authorized=authorized)
    if status_note:
        text = f"{text}\n\n{status_note}"

    keyboard = build_main_menu_keyboard(
        webapp_url=config.webapp_webview_url,
        browser_url=config.webapp_browser_url,
    )

    hero_image = config.hero_image_url
    if hero_image:
        await message.answer_photo(hero_image, caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

    if experimental_menu:
        crm_entry = create_crm_entry_point(
            webapp_url=config.webapp_browser_url,
            bot_username=config.bot_username,
        )
        quick_actions_markup = build_quick_actions_keyboard(crm_entry=crm_entry)
        await message.answer("Быстрые действия:", reply_markup=quick_actions_markup)


async def process_cancel(
    message: Message,
    state: FSMContext,
    backend: BackendClient,
    access_token: str | None,
    config: Config,
    *,
    request_id: str | None = None,
    experimental_menu: bool = False,
) -> None:
    await state.clear()
    await message.answer(CANCELLED_TEXT)
    await process_start(
        message,
        backend,
        access_token,
        config,
        request_id=request_id,
        experimental_menu=experimental_menu,
    )


@router.message(CommandStart())
async def on_start_command(
    message: Message,
    backend: BackendClient,
    access_token: str | None,
    config: Config,
    request_id: str | None,
    experimental_menu: bool,
) -> None:
    await process_start(
        message,
        backend,
        access_token,
        config,
        request_id=request_id,
        experimental_menu=experimental_menu,
    )


@router.message(Command("cancel"))
async def on_cancel_command(
    message: Message,
    state: FSMContext,
    backend: BackendClient,
    access_token: str | None,
    config: Config,
    request_id: str | None,
    experimental_menu: bool,
) -> None:
    await process_cancel(
        message,
        state,
        backend,
        access_token,
        config,
        request_id=request_id,
        experimental_menu=experimental_menu,
    )


@router.message(Command("cansel"))
async def on_cansel_alias(
    message: Message,
    state: FSMContext,
    backend: BackendClient,
    access_token: str | None,
    config: Config,
    request_id: str | None,
    experimental_menu: bool,
) -> None:
    await process_cancel(
        message,
        state,
        backend,
        access_token,
        config,
        request_id=request_id,
        experimental_menu=experimental_menu,
    )


__all__ = ["router", "process_start", "process_cancel"]
