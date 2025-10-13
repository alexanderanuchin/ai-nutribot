from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Iterable, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.logging_utils import get_request_id
from ..backend_client import (
    AuthResult,
    BackendAuthError,
    BackendClient,
    BackendError,
    BackendNetworkError,
    BackendValidationError,
)

router = Router()
logger = logging.getLogger("audit.wallet")

TOPUP_AMOUNTS: Tuple[int, ...] = (50, 100)
TOPUP_SOURCE = "telegram_bot_invoice"


def _authorization_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url:
        if webapp_url.lower().startswith("https://"):
            builder.button(text="Открыть кабинет", web_app=WebAppInfo(url=webapp_url))
        else:
            builder.button(text="Открыть кабинет", url=webapp_url)
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
        lines.append("\nПополнение Stars недоступно: Telegram временно отключил покупки в вашем регионе.")
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


async def _manual_topup(
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    refresh_token: str | None,
    *,
    amount: int,
    idempotency_key: str,
    metadata: dict,
    notify_retry,
):
    attempt = 0
    last_error: Exception | None = None
    while attempt < 2:
        try:
            result = await backend.manual_stars_topup(
                access_token,
                refresh_token,
                amount=amount,
                idempotency_key=idempotency_key,
                source=TOPUP_SOURCE,
                metadata=metadata,
            )
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
    raise BackendError("Не удалось обработать пополнение")


def _parse_invoice_payload(payload: str) -> dict:
    parts = (payload or "").split(";")
    result = {}
    for item in parts:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key] = value
    return result


def _build_invoice_payload(user_id: int, amount: int, *, rid: str | None = None) -> str:
    token = uuid.uuid4().hex
    parts = [f"uid={user_id}", f"amt={amount}", f"token={token}"]
    if rid:
        parts.append(f"rid={rid}")
    return ";".join(parts)


def build_stars_topup_invoice(
    user_id: int,
    amount: int,
    *,
    comment: str | None = None,
    rid: str | None = None,
) -> dict:
    description = f"Быстрое пополнение на {amount} XTR."
    if comment:
        comment_text = comment.strip()
        if comment_text:
            # Telegram ограничивает описание инвойса 255 символами
            short_comment = comment_text[:180]
            description += f"\nКомментарий: {short_comment}"

    rid_to_use = rid or get_request_id()
    payload = _build_invoice_payload(user_id, amount, rid=rid_to_use)
    payload_meta = _parse_invoice_payload(payload)
    token_prefix = (payload_meta.get("token") or "")[:8] if payload_meta else ""
    logger.info(
        "wallet invoice_created rid=%s telegram_user_id=%s amount=%s currency=%s has_comment=%s token_prefix=%s",
        rid_to_use,
        user_id,
        amount,
        "XTR",
        bool(comment and comment.strip()),
        token_prefix,
    )
    prices = [LabeledPrice(label=f"Пополнение {amount} XTR", amount=amount)]
    return {
        "title": "Пополнение баланса Stars",
        "description": description,
        "currency": "XTR",
        "prices": prices,
        "payload": payload,
        "provider_token": "",
    }


async def _ensure_authorized(message: Message, webapp_url: str) -> None:
    await message.answer(
        "Сначала авторизуйтесь через WebApp, чтобы увидеть баланс.",
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
        await callback.message.answer(
            "Сначала авторизуйтесь через WebApp, чтобы увидеть баланс.",
            reply_markup=_authorization_keyboard(webapp_url),
        )
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
        await callback.message.answer(
            "Сессия истекла. Авторизуйтесь через WebApp.",
            reply_markup=_authorization_keyboard(webapp_url),
        )
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
        await callback.message.answer(
            "Сначала авторизуйтесь через WebApp, чтобы пополнить баланс.",
            reply_markup=_authorization_keyboard(webapp_url),
        )
        await callback.answer()
        return
    if state_data.get("stars_purchase_blocked"):
        await callback.message.answer(
            "Пополнение Stars недоступно: Telegram временно отключил покупки в вашем регионе."
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
        "wallet quick_topup rid=%s telegram_user_id=%s amount=%s",
        rid,
        callback.from_user.id,
        amount,
    )
    invoice = build_stars_topup_invoice(
        callback.from_user.id,
        amount,
        rid=rid,
    )
    await callback.message.answer_invoice(**invoice)
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    if query.from_user is None:
        await query.answer(
            ok=False,
            error_message="Не удалось определить ваш аккаунт Telegram. Попробуйте снова через несколько минут.",
        )
        logger.error("wallet pre_checkout missing_user rid=%s", get_request_id())
        return

    payload_meta = _parse_invoice_payload(query.invoice_payload)
    requested_user = payload_meta.get("uid") if payload_meta else None
    try:
        requested_user_id = int(requested_user) if requested_user is not None else None
    except (TypeError, ValueError):
        requested_user_id = None

    if requested_user_id is not None and requested_user_id != query.from_user.id:
        await query.answer(
            ok=False,
            error_message="Этот счёт принадлежит другому пользователю. Попросите бота выписать новый счёт.",
        )
        logger.warning(
            "wallet pre_checkout user_mismatch rid=%s requested=%s actual=%s",
            get_request_id(),
            requested_user_id,
            query.from_user.id,
        )
        return

    currency = (query.currency or "").upper()
    amount = int(query.total_amount)
    logger.info(
        "wallet pre_checkout received rid=%s telegram_user_id=%s amount=%s currency=%s payload_keys=%s",
        get_request_id(),
        query.from_user.id,
        amount,
        currency,
        sorted(payload_meta.keys()) if payload_meta else [],
    )
    if currency != "XTR":
        await query.answer(
            ok=False,
            error_message="Оплата может быть проведена только в Telegram Stars (XTR).",
        )
        logger.warning(
            "wallet pre_checkout invalid_currency rid=%s currency=%s",
            get_request_id(),
            currency,
        )
        return

    if amount not in TOPUP_AMOUNTS:
        await query.answer(
            ok=False,
            error_message="Сумма счёта не поддерживается. Создайте новый счёт через /wallet.",
        )
        logger.warning(
            "wallet pre_checkout invalid_amount rid=%s amount=%s",
            get_request_id(),
            amount,
        )
        return

    await query.answer(ok=True)
    logger.info(
        "wallet pre_checkout approved rid=%s telegram_user_id=%s amount=%s",
        get_request_id(),
        query.from_user.id,
        amount,
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
    payload_meta = _parse_invoice_payload(payment.invoice_payload)
    rid = get_request_id()
    logger.info(
        "wallet payment_received rid=%s telegram_user_id=%s charge_id=%s provider_charge_id=%s amount=%s currency=%s "
        "payload_keys=%s",
        rid,
        getattr(message.from_user, "id", None),
        charge_id,
        payment.provider_payment_charge_id,
        amount,
        currency,
        sorted(payload_meta.keys()) if payload_meta else [],
    )

    if currency != "XTR":
        await message.answer("Получен платёж в неподдерживаемой валюте. Обратитесь в поддержку.")
        return
    if not charge_id:
        await message.answer("Не удалось идентифицировать платеж. Напишите в поддержку.")
        return
    user = message.from_user
    if user is None:
        await message.answer("Не удалось сопоставить платеж с пользователем Telegram.")
        return

    payload_meta = _parse_invoice_payload(payment.invoice_payload)
    if payload_meta:
        uid_raw = payload_meta.get("uid")
        try:
            uid = int(uid_raw)
        except (TypeError, ValueError):
            uid = user.id
        if uid != user.id:
            await message.answer(
                "Получен платёж от другого пользователя. Свяжитесь с поддержкой, если это ошибка."
            )
            logger.warning(
                "wallet payment_user_mismatch rid=%s expected=%s actual=%s charge_id=%s",
                rid,
                uid,
                user.id,
                charge_id,
            )
            return

    idempotency_key = f"telegram-stars:{user.id}:{charge_id}"
    logger.info(
        "wallet payment_report rid=%s telegram_user_id=%s amount=%s currency=%s charge_id=%s idempotency_key=%s "
        "has_comment=%s",
        rid,
        user.id,
        amount,
        currency,
        charge_id,
        idempotency_key,
        bool((payload_meta or {}).get("comment")),
    )
    try:
        await backend.report_stars_payment(
            user_id=user.id,
            amount=amount,
            charge_id=charge_id,
        )
        logger.info(
            "wallet payment_report_success rid=%s telegram_user_id=%s charge_id=%s",
            rid,
            user.id,
            charge_id,
        )
    except BackendValidationError as exc:
        details = exc.errors if isinstance(exc.errors, dict) else {"detail": str(exc)}
        detail_msg = details.get("detail") or details.get("charge_id") or str(details)
        logger.error(
            "wallet payment_report_validation rid=%s telegram_user_id=%s charge_id=%s error=%s",
            rid,
            user.id,
            charge_id,
            details,
        )
        await message.answer(
            "Оплата получена, но не удалось зафиксировать зачисление: " f"{detail_msg}"
        )
        return
    except BackendError as exc:
        logger.error(
            "wallet payment_report_error rid=%s telegram_user_id=%s charge_id=%s error=%s",
            rid,
            user.id,
            charge_id,
            exc,
        )
        await message.answer(
            "Оплата получена, но при попытке зачислить Stars произошла ошибка. "
            "Команда уже уведомлена.\n" f"{exc}"
        )
        return

    await message.answer(f"Баланс пополнен на {amount} XTR. Спасибо!")


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