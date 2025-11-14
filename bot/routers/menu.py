from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.backend_client import BackendClient
from bot.config import Config
from bot.handlers.plan import history_command as handle_history_command
from bot.handlers.plan import plan_command as handle_plan_command
from bot.handlers.profile_wizard import on_profile_command as handle_profile_command
from bot.handlers.support import (
    pay_support_command as handle_pay_support_command,
    support_command as handle_support_command,
    terms_command as handle_terms_command,
)
from bot.handlers.wallet import wallet_command as handle_wallet_command
from bot.keyboards.inline import QuickAction, QuickActionCallback
from bot.keyboards.main_menu import MainMenuAction, MainMenuCallback
from bot.logkit import get_request_id
from bot.routers.commands import process_start

logger = logging.getLogger("bot.menu")

router = Router(name="menu")

_TEXT_ACTIONS = {
    "🏠 Главная": MainMenuAction.PROFILE,  # fallback to process_start via handler below
    "👤 Профиль": MainMenuAction.PROFILE,
    "🧾 Тариф": None,
    "📜 История": None,
    "👛 Кошелёк": MainMenuAction.WALLET,
    "🆘 Поддержка": MainMenuAction.SUPPORT,
    "💳 Оплата/помощь": None,
    "📄 Условия": MainMenuAction.TERMS,
}


async def _handle_main_action(
    action: MainMenuAction,
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    config: Config,
    *,
    request_id: str | None,
) -> None:
    if action == MainMenuAction.PROFILE:
        await handle_profile_command(message, backend, state, access_token, config.webapp_url)
        return
    if action == MainMenuAction.WALLET:
        await handle_wallet_command(message, backend, state, access_token)
        return
    if action == MainMenuAction.SUPPORT:
        await handle_support_command(message, support_url=config.support_url)
        return
    if action == MainMenuAction.TERMS:
        await handle_terms_command(message, terms_url=config.terms_url, privacy_url=config.privacy_url)
        return
    logger.debug("unhandled main action", extra={"rid": request_id or get_request_id(), "action": action.value})


@router.message(
    F.text.in_(set(_TEXT_ACTIONS.keys()))
)
async def on_main_menu_button(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    config: Config,
    request_id: str | None,
    experimental_menu: bool,
) -> None:
    text = (message.text or "").strip()
    rid = request_id or get_request_id()
    if text == "🏠 Главная":
        await process_start(
            message,
            backend,
            access_token,
            config,
            request_id=rid,
            experimental_menu=experimental_menu,
        )
        return
    action = _TEXT_ACTIONS.get(text)
    if action:
        await _handle_main_action(
            action,
            message,
            backend,
            state,
            access_token,
            config,
            request_id=rid,
        )
        return
    if text == "🧾 Тариф":
        await handle_plan_command(message, backend, state, access_token)
        return
    if text == "📜 История":
        await handle_history_command(message, backend, state, access_token)
        return
    if text == "💳 Оплата/помощь":
        await handle_pay_support_command(message, support_url=config.support_url)
        return
    logger.debug("menu button ignored", extra={"text": text, "rid": rid})


@router.callback_query(MainMenuCallback.filter())
async def on_main_menu_callback(
    callback: CallbackQuery,
    callback_data: MainMenuCallback,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    config: Config,
    request_id: str | None,
    experimental_menu: bool,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await _handle_main_action(
        callback_data.action,
        callback.message,
        backend,
        state,
        access_token,
        config,
        request_id=request_id,
    )
    await callback.answer()


@router.callback_query(QuickActionCallback.filter())
async def on_quick_action(
    callback: CallbackQuery,
    callback_data: QuickActionCallback,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
) -> None:
    action = callback_data.action
    if action == QuickAction.WALLET_TOP_UP:
        if callback.message:
            await handle_wallet_command(
                callback.message,
                backend=backend,
                state=state,
                access_token=access_token,
            )
        await callback.answer()
        return
    if action == QuickAction.CHANGE_PLAN:
        if callback.message:
            await handle_plan_command(
                callback.message,
                backend=backend,
                state=state,
                access_token=access_token,
            )
        await callback.answer()
        return
    logger.warning(
        "quick action not supported",
        extra={"action": action, "rid": get_request_id()},
    )
    await callback.answer()


__all__ = ["router"]
