from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.backend_client import (
    AuthResult,
    BackendAuthError,
    BackendClient,
    BackendError,
    BackendNetworkError,
    BackendValidationError,
)
from bot.constants import STARS_BLOCKED_MESSAGE, TOPUP_AMOUNTS as DEFAULT_TOPUP_AMOUNTS
from bot.handlers.plan import resume_plan_generation_if_needed
from bot.logkit import get_request_id
from bot.payments import build_stars_topup_invoice, parse_invoice_payload, plan_topup_payload

router = Router()
logger = logging.getLogger("audit.wallet")

TOPUP_AMOUNTS: Tuple[int, ...] = DEFAULT_TOPUP_AMOUNTS
MIN_TOPUP_AMOUNT = 1
MAX_TOPUP_AMOUNT = 10000


def _authorization_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url:
        if webapp_url.lower().startswith("https://"):
            builder.button(text="Открыть приложение", web_app=WebAppInfo(url=webapp_url))
        else:
            builder.button(text="Открыть приложение", url=webapp_url)
    builder.button(text="↩️ В меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


def _wallet_keyboard(*, stars_blocked: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not stars_blocked:
        for amount in TOPUP_AMOUNTS:
            builder.button(text=f"Пополнить {amount} XTR", callback_data=f"wallet:topup:{amount}")
    builder.button(text="↩️ В меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


async def _apply_tokens(state: FSMContext, result: AuthResult) -> None:
    updates = {}
    if result.access:
        updates["access_token"] = result.access
    if result.refresh:
        updates["refresh_token"] = result.refresh
    if updates:
        await state.update_data(**updates)


async def _get_tokens(
    state: FSMContext,
    fallback_access: str | None,
    *,
    user_id: int | None = None,
) -> Tuple[str | None, str | None]:
    data = await state.get_data()
    session_user_id = data.get("session_user_id")
    if user_id is not None and session_user_id is not None:
        try:
            if int(session_user_id) != int(user_id):
                return None, None
        except (TypeError, ValueError):
            return None, None
    access_token = data.get("access_token") or fallback_access
    refresh_token = data.get("refresh_token")
    return access_token, refresh_token


def _format_transaction_line(item: dict) -> str:
    raw_date = item.get("occurred_at")
    try:
        occurred_at = datetime.fromisoformat(str(raw_date)) if raw_date else None
    except ValueError:
        occurred_at = None
    if occurred_at:
        date_part = occurred_at.strftime("%d.%m.%Y")
    else:
        date_part = str(raw_date or "—")
    direction = str(item.get("direction"))
    sign = "+" if direction == "in" else "-"
    amount = int(item.get("amount", 0))
    return f"{date_part} {sign}{amount} XTR"


def _format_wallet_message(payload: dict) -> str:
    balance = payload.get("balance", {})
    amount = balance.get("amount", 0)
    currency = balance.get("currency", "XTR")
    lines = [f"Ваш баланс: {amount} {currency}"]
    transactions = payload.get("transactions") or []
    stars_blocked = bool(payload.get("stars_purchase_blocked"))
    if transactions:
        lines.append("\nПоследние операции:")
        for item in transactions[:3]:
            lines.append(_format_transaction_line(item))
    else:
        lines.append("\nПока нет операций.")
    if stars_blocked:
        lines.append("\n" + STARS_BLOCKED_MESSAGE)
        lines.append("Для вопросов по оплате используйте /paysupport.")
    else:
        lines.append("\nВыберите сумму для быстрого пополнения 👇")
        lines.append("\nНажимая «Пополнить», вы подтверждаете, что ознакомились с /terms и согласны с ними.")
        lines.append("Для вопросов по оплате используйте /paysupport.")
    return "\n".join(lines)


async def _load_wallet_payload(
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    refresh_token: str | None,
    notify_retry,
):
    attempt = 0
    last_error: Exception | None = None
    while attempt < 2:
        try:
            result = await backend.get_my_stars(access_token, refresh_token)
            await _apply_tokens(state, result)
            payload = result.payload
            await state.update_data(
                stars_purchase_blocked=bool(payload.get("stars_purchase_blocked"))
            )
            return payload
        except BackendAuthError as exc:
            await state.update_data(access_token=None, refresh_token=None)
            raise exc
        except BackendNetworkError as exc:
            last_error = exc
            attempt += 1
            if attempt == 1:
                await notify_retry()
                access_token, refresh_token = await _get_tokens(state, access_token)
                continue
            break
        except BackendError as exc:
            raise exc
    if last_error:
        raise last_error
    raise BackendError("Не удалось получить данные кошелька")


async def _load_bot_balance(
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    refresh_token: str | None,
    notify_retry,
):
    attempt = 0
    last_error: Exception | None = None
    while attempt < 2:
        try:
            result = await backend.get_bot_stars_balance(access_token, refresh_token)
            await _apply_tokens(state, result)
            return result.payload
        except BackendAuthError as exc:
            await state.update_data(access_token=None, refresh_token=None)
            raise exc
        except BackendNetworkError as exc:
            last_error = exc
            attempt += 1
            if attempt == 1:
                await notify_retry()
                access_token, refresh_token = await _get_tokens(state, access_token)
                continue
            break
        except BackendError as exc:
            raise exc
    if last_error:
        raise last_error
    raise BackendError("Не удалось получить баланс бота")


async def _ensure_authorized(message: Message, webapp_url: str) -> None:
    await message.answer(
        "Нужно войти, чтобы посмотреть кошелёк.",
        reply_markup=_authorization_keyboard(webapp_url),
    )


async def _ensure_admin_authorized(message: Message) -> None:
    await message.answer("Команда доступна только администраторам.")


@router.message(Command("wallet"))
async def wallet_command(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    webapp_url: str,
):
    if not access_token:
        await _ensure_authorized(message, webapp_url)
        return
    data = await state.get_data()
    refresh_token = data.get("refresh_token")

    async def notify_retry():
        await message.answer("Не смогли получить данные, пробую ещё раз…")

    try:
        payload = await _load_wallet_payload(
            backend,
            state,
            access_token,
            refresh_token,
            notify_retry=notify_retry,
        )
    except BackendAuthError:
        await _ensure_authorized(message, webapp_url)
        return
    except BackendNetworkError:
        await message.answer("Не удалось получить данные кошелька. Попробуйте позже.")
        return
    except BackendError as exc:
        await message.answer(f"Не удалось получить данные кошелька.\n{exc}")
        return

    text = _format_wallet_message(payload)
    stars_blocked = bool(payload.get("stars_purchase_blocked"))
    await message.answer(text, reply_markup=_wallet_keyboard(stars_blocked=stars_blocked))


@router.callback_query(F.data == "wallet:open")
async def wallet_open_callback(
    callback: CallbackQuery,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    webapp_url: str,
):
    if callback.message is None:
        await callback.answer()
        return

    if not access_token:
        await _ensure_authorized(callback.message, webapp_url)
        await callback.answer()
        return

    data = await state.get_data()
    refresh_token = data.get("refresh_token")

    async def notify_retry():
        await callback.message.answer("Не смогли получить данные, пробую ещё раз…")

    try:
        payload = await _load_wallet_payload(
            backend,
            state,
            access_token,
            refresh_token,
            notify_retry=notify_retry,
        )
    except BackendAuthError:
        await _ensure_authorized(callback.message, webapp_url)
        await callback.answer()
        return
    except BackendNetworkError:
        await callback.message.answer("Не удалось получить данные кошелька. Попробуйте позже.")
        await callback.answer()
        return
    except BackendError as exc:
        await callback.message.answer(f"Не удалось получить данные кошелька.\n{exc}")
        await callback.answer()
        return

    stars_blocked = bool(payload.get("stars_purchase_blocked"))
    await callback.message.answer(
        _format_wallet_message(payload), reply_markup=_wallet_keyboard(stars_blocked=stars_blocked)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wallet:topup:"))
async def wallet_topup_callback(
    callback: CallbackQuery,
    state: FSMContext,
    access_token: str | None,
    webapp_url: str,
    provider_token: str | None,
):
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    state_data = await state.get_data()
    from_user_id = getattr(callback.from_user, "id", None)
    stored_access_token, _ = await _get_tokens(
        state,
        access_token,
        user_id=from_user_id,
    )
    if not stored_access_token:
        await _ensure_authorized(callback.message, webapp_url)
        await callback.answer()
        return
    if state_data.get("stars_purchase_blocked"):
        await callback.message.answer(
            STARS_BLOCKED_MESSAGE
        )
        await callback.answer()
        return
    try:
        _, _, amount_raw = callback.data.partition("wallet:topup:")
        amount = int(amount_raw)
    except (TypeError, ValueError):
        await callback.answer("Неизвестная сумма", show_alert=True)
        return

    rid = get_request_id()
    logger.info(
        "wallet quick_topup",
        extra={
            "rid": rid,
            "telegram_user_id": getattr(callback.from_user, "id", None),
            "amount": amount,
            "currency": "XTR",
            "action": "wallet_topup",
        },
    )
    payload_extra = plan_topup_payload(state_data)
    invoice = build_stars_topup_invoice(
        callback.from_user.id,
        amount,
        rid=rid,
        provider_token=provider_token,
        payload_extra=payload_extra,
    )
    await callback.message.answer_invoice(**invoice)
    if payload_extra:
        pending = state_data.get("pending_action")
        if isinstance(pending, dict):
            updated = {**pending, "status": "invoice_sent"}
            await state.update_data(pending_action=updated)
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    rid = get_request_id()

    if query.from_user is None:
        await query.answer(
            ok=False,
            error_message="Не удалось определить ваш аккаунт Telegram. Попробуйте снова через несколько минут.",
        )
        logger.error(
            "wallet pre_checkout missing_user",
            extra={"rid": rid},
        )
        return

    payload_meta = parse_invoice_payload(query.invoice_payload)
    requested_user = payload_meta.get("uid") if payload_meta else None
    try:
        requested_user_id = int(requested_user) if requested_user is not None else None
    except (TypeError, ValueError):
        requested_user_id = None

    intent = payload_meta.get("intent") if payload_meta else None
    action = payload_meta.get("action") if payload_meta else None
    attempt_id: int | None = None
    if payload_meta:
        raw_attempt = payload_meta.get("aid")
        if raw_attempt is not None:
            try:
                attempt_id = int(raw_attempt)
            except (TypeError, ValueError):
                attempt_id = None

    if requested_user_id is not None and requested_user_id != query.from_user.id:
        await query.answer(
            ok=False,
            error_message="Этот счёт принадлежит другому пользователю. Попросите бота выписать новый счёт.",
        )
        logger.warning(
            "wallet pre_checkout user_mismatch",
            extra={
                "rid": rid,
                "requested_user_id": requested_user_id,
                "actual_user_id": query.from_user.id,
            },
        )
        return

    currency = (query.currency or "").upper()
    amount = int(query.total_amount)
    payload_keys = sorted(payload_meta.keys()) if payload_meta else []
    logger.info(
        "wallet pre_checkout received",
        extra={
            "rid": rid,
            "telegram_user_id": query.from_user.id,
            "amount": amount,
            "currency": currency,
            "payload_keys": payload_keys,
            "attempt_id": attempt_id,
            "action": action,
            "intent": intent,
        },
    )
    if currency != "XTR":
        await query.answer(
            ok=False,
            error_message="Оплата может быть проведена только в Telegram Stars (XTR).",
        )
        logger.warning(
            "wallet pre_checkout invalid_currency",
            extra={"rid": rid, "currency": currency},
        )
        return

    if amount < MIN_TOPUP_AMOUNT:
        await query.answer(
            ok=False,
            error_message=f"Минимальная сумма пополнения — {MIN_TOPUP_AMOUNT} XTR.",
        )
        logger.warning(
            "wallet pre_checkout below_min",
            extra={
                "rid": rid,
                "amount": amount,
                "min_amount": MIN_TOPUP_AMOUNT,
            },
        )
        return

    if amount > MAX_TOPUP_AMOUNT:
        await query.answer(
            ok=False,
            error_message="Сумма слишком большая. Попробуйте уменьшить пополнение.",
        )
        logger.warning(
            "wallet pre_checkout above_max",
            extra={
                "rid": rid,
                "amount": amount,
                "max_amount": MAX_TOPUP_AMOUNT,
            },
        )
        return

    await query.answer(ok=True)
    logger.info(
        "wallet pre_checkout approved",
        extra={
            "rid": rid,
            "telegram_user_id": query.from_user.id,
            "amount": amount,
            "currency": currency,
            "attempt_id": attempt_id,
            "action": action,
            "intent": intent,
        },
    )


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
):
    payment = message.successful_payment
    if payment is None:
        return

    charge_id = payment.telegram_payment_charge_id or payment.provider_payment_charge_id
    amount = int(payment.total_amount)
    currency = payment.currency
    payload_meta = parse_invoice_payload(payment.invoice_payload)
    payload_keys = sorted(payload_meta.keys()) if payload_meta else []
    rid = get_request_id()
    user = message.from_user
    user_id = getattr(user, "id", None)

    intent: str | None = payload_meta.get("intent") if payload_meta else None
    action: str | None = payload_meta.get("action") if payload_meta else None
    attempt_id: int | None = None
    expected_user_id = user_id
    if payload_meta:
        uid_raw = payload_meta.get("uid")
        try:
            expected_user_id = int(uid_raw) if uid_raw is not None else user_id
        except (TypeError, ValueError):
            expected_user_id = user_id
        raw_attempt = payload_meta.get("aid")
        if raw_attempt is not None:
            try:
                attempt_id = int(raw_attempt)
            except (TypeError, ValueError):
                attempt_id = None

    logger.info(
        "wallet payment_received",
        extra={
            "rid": rid,
            "telegram_user_id": user_id,
            "charge_id": charge_id,
            "provider_charge_id": payment.provider_payment_charge_id,
            "amount": amount,
            "currency": currency,
            "payload_keys": payload_keys,
            "attempt_id": attempt_id,
            "intent": intent,
            "action": action,
        },
    )

    if currency != "XTR":
        await message.answer("Получен платёж в неподдерживаемой валюте. Обратитесь в поддержку.")
        return
    if not charge_id:
        await message.answer("Не удалось идентифицировать платеж. Напишите в поддержку.")
        return
    if user is None:
        await message.answer("Не удалось сопоставить платеж с пользователем Telegram.")
        return

    if expected_user_id is not None and expected_user_id != user.id:
        await message.answer(
            "Получен платёж от другого пользователя. Свяжитесь с поддержкой, если это ошибка."
        )
        logger.warning(
            "wallet payment_user_mismatch",
            extra={
                "rid": rid,
                "expected_user_id": expected_user_id,
                "actual_user_id": user.id,
                "charge_id": charge_id,
            },
        )
        return

    state_data = await state.get_data()
    if intent == "plan_topup" and attempt_id is not None:
        pending = state_data.get("pending_action")
        if isinstance(pending, dict):
            try:
                pending_attempt = int(pending.get("attempt_id"))
            except (TypeError, ValueError):
                pending_attempt = None
            if pending_attempt == attempt_id:
                updated = {**pending, "status": "payment_confirmed"}
                await state.update_data(pending_action=updated)

    idempotency_key = f"telegram-stars:{user.id}:{charge_id}"
    logger.info(
        "wallet payment_report",
        extra={
            "rid": rid,
            "telegram_user_id": user.id,
            "amount": amount,
            "currency": currency,
            "charge_id": charge_id,
            "idempotency_key": idempotency_key,
            "has_comment": bool((payload_meta or {}).get("comment")),
            "payment_attempt_id": attempt_id,
            "intent": intent,
            "action": action,
        },
    )
    try:
        await backend.report_stars_payment(
            user_id=user.id,
            amount=amount,
            charge_id=charge_id,
            payment_attempt_id=attempt_id,
        )
        logger.info(
            "wallet payment_report_success",
            extra={
                "rid": rid,
                "telegram_user_id": user.id,
                "charge_id": charge_id,
                "payment_attempt_id": attempt_id,
                "amount": amount,
                "currency": currency,
                "action": action,
            },
        )
    except BackendValidationError as exc:
        details = exc.errors if isinstance(exc.errors, dict) else {"detail": str(exc)}
        code = details.get("code") if isinstance(details, dict) else None
        if details.get("stars_purchase_blocked") or code in {"purchases_disabled", "user_not_found"}:
            await state.update_data(stars_purchase_blocked=True)
        detail_msg = details.get("detail") or details.get("charge_id") or str(details)
        logger.error(
            "wallet payment_report_validation",
            extra={
                "rid": rid,
                "telegram_user_id": user.id,
                "charge_id": charge_id,
                "error": details,
                "code": code,
            },
        )
        if code == "purchases_disabled":
            await message.answer(STARS_BLOCKED_MESSAGE)
        elif code == "user_not_found":
            await message.answer(
                "Telegram не смог найти ваш аккаунт для оплаты Stars. "
                "Убедитесь, что вы авторизованы в мини-приложении и попробуйте снова."
            )
        else:
            await message.answer(
                "Оплата получена, но не удалось зафиксировать зачисление: " f"{detail_msg}"
            )
        return
    except BackendError as exc:
        logger.error(
            "wallet payment_report_error",
            extra={
                "rid": rid,
                "telegram_user_id": user.id,
                "charge_id": charge_id,
                "error": str(exc),
            },
        )
        await message.answer(
            "Оплата получена, но при попытке зачислить Stars произошла ошибка. "
            "Команда уже уведомлена.\n" f"{exc}"
        )
        return

    resumed = False
    plan_resumed = False
    if intent == "plan_topup" and attempt_id is not None and (action in {None, "generate_plan"}):
        plan_resumed = await resume_plan_generation_if_needed(
            message,
            backend,
            state,
            rid=rid,
            attempt_id=attempt_id,
            intent=intent,
        )
        resumed = plan_resumed
    if not resumed:
        await message.answer(f"Баланс пополнен на {amount} XTR. Спасибо!")
    if not resumed:
        resumed = await resume_plan_generation_if_needed(
            message,
            backend,
            state,
            rid=rid,
        )
    if resumed:
        logger.info(
            "wallet payment_resume_triggered",
            extra={
                "rid": rid,
                "telegram_user_id": getattr(message.from_user, "id", None),
                "amount": amount,
                "plan_resume": plan_resumed,
                "payment_attempt_id": attempt_id,
                "currency": currency,
                "action": action,
            },
        )


def _is_admin(user_id: int | None, admin_ids: Iterable[int]) -> bool:
    if user_id is None:
        return False
    return user_id in set(admin_ids)


@router.message(Command("bot_stars"))
async def bot_stars_command(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    admin_ids: Iterable[int],
):
    user_id = getattr(message.from_user, "id", None)
    if not admin_ids or not _is_admin(user_id, admin_ids):
        await _ensure_admin_authorized(message)
        return
    if not access_token:
        await message.answer("Авторизуйтесь через WebApp, чтобы посмотреть баланс бота.")
        return

    data = await state.get_data()
    refresh_token = data.get("refresh_token")

    async def notify_retry():
        await message.answer("Не смогли получить данные, пробую ещё раз…")

    try:
        payload = await _load_bot_balance(
            backend,
            state,
            access_token,
            refresh_token,
            notify_retry=notify_retry,
        )
    except BackendAuthError:
        await message.answer("Сессия истекла. Авторизуйтесь заново через WebApp.")
        return
    except BackendNetworkError:
        await message.answer("Не удалось получить баланс бота. Попробуйте позже.")
        return
    except BackendError as exc:
        await message.answer(f"Не удалось получить баланс бота.\n{exc}")
        return

    balance = payload.get("balance", {})
    amount = balance.get("amount", 0)
    currency = balance.get("currency", "XTR")
    updated = balance.get("updated_at")
    lines = [f"Баланс бота: {amount} {currency}"]
    if updated:
        lines.append(f"Обновлено: {updated}")
    await message.answer("\n".join(lines))