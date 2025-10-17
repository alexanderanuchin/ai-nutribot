from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.backend_client import BackendClient
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
from bot.routers.commands import process_start
from bot.logging_utils import get_request_id

logger = logging.getLogger("bot.menu")

router = Router(name="menu")


@router.message(F.text.in_({
    "🏠 Главная",
    "👤 Профиль",
    "🧾 Тариф",
    "📜 История",
    "👛 Кошелёк",
    "🆘 Поддержка",
    "💳 Оплата/помощь",
    "📄 Условия",
}))
async def on_main_menu_button(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    webapp_url: str,
    bot_username: str,
    request_id: str | None,
) -> None:
    text = (message.text or "").strip()
    rid = request_id or get_request_id()
    if text == "🏠 Главная":
        await process_start(
            message,
            backend,
            access_token,
            webapp_url,
            bot_username,
            request_id,
        )
        return
    if text == "👤 Профиль":
        await handle_profile_command(
            message,
            backend,
            state,
            access_token,
            webapp_url,
        )
        return
    if text == "🧾 Тариф":
        await handle_plan_command(
            message,
            backend,
            state,
            access_token,
        )
        return
    if text == "📜 История":
        await handle_history_command(
            message,
            backend,
            state,
            access_token,
        )
        return
    if text == "👛 Кошелёк":
        await handle_wallet_command(
            message,
            backend,
            state,
            access_token,
        )
        return
    if text == "🆘 Поддержка":
        await handle_support_command(message)
        return
    if text == "💳 Оплата/помощь":
        await handle_pay_support_command(message)
        return
    if text == "📄 Условия":
        await handle_terms_command(message)
        return

    logger.debug("menu button ignored", extra={"text": text, "rid": rid})


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