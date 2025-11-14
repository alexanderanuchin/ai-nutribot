"""Handlers for nutrition plan flow."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.backend_client import (
    AuthResult,
    BackendAuthError,
    BackendClient,
    BackendError,
    BackendValidationError,
)
from bot.constants import STARS_BLOCKED_MESSAGE
from bot.logkit import get_request_id
from bot.keyboards.plan import (
    generate_keyboard,
    period_keyboard,
    plan_topup_keyboard,
    regeneration_options_keyboard,
    summary_actions_keyboard,
)
from bot.payments import build_stars_topup_invoice, plan_topup_payload
from bot.states import PlanGeneration

router = Router()
logger = logging.getLogger("audit.plan")


PLAN_ACTION = "generate_plan"


async def _save_tokens(state: FSMContext, result: AuthResult) -> None:
    updates: Dict[str, Any] = {}
    if result.access:
        updates["access_token"] = result.access
    if result.refresh:
        updates["refresh_token"] = result.refresh
    if updates:
        await state.update_data(**updates)


async def _reset_state(state: FSMContext, *, keep_tokens: bool = True) -> None:
    if not keep_tokens:
        await state.clear()
        return
    data = await state.get_data()
    tokens = {key: data.get(key) for key in ("access_token", "refresh_token") if data.get(key)}
    await state.clear()
    if tokens:
        await state.update_data(**tokens)


def _format_profile_hint(profile: Dict[str, Any]) -> str:
    goal = profile.get("goals") or profile.get("goal")
    goal_map = {
        "lose": "снижение веса",
        "lose_weight": "снижение веса",
        "gain": "набор массы",
        "gain_muscle": "набор массы",
        "maintain": "поддержание формы",
        "keep_fit": "поддержание формы",
        "recomp": "ресинтез",
    }
    city = profile.get("city") or "—"
    budget = profile.get("budget") or profile.get("daily_budget") or "—"
    allergies = profile.get("allergies") or []
    allergies_text = ", ".join(allergies) if allergies else "нет"
    return (
        "Готовим план на основе профиля:\n"
        f"Город: {city}\n"
        f"Бюджет: {budget} ₽ в день\n"
        f"Цель: {goal_map.get(goal, goal or 'не указана')}\n"
        f"Аллергии: {allergies_text}"
    )


def _format_plan_summary(summary: Dict[str, Any]) -> str:
    lines = [
        f"Период: {summary.get('period_days', '—')} дн.",
        f"Калории: {summary.get('daily_kcal', '—')} ккал",
        "Б/Ж/У: {}/{}/{} г".format(
            summary.get("protein_g", "—"),
            summary.get("fat_g", "—"),
            summary.get("carbs_g", "—"),
        ),
        f"Приёмов пищи: {summary.get('meals_total', '—')} (уникальных блюд: {summary.get('unique_dishes', '—')})",
        f"Стоимость ~ {summary.get('estimated_cost_rub_per_day', '—')} ₽ в день",
    ]
    notes = summary.get("notes")
    if isinstance(notes, str) and notes:
        lines.append(f"Примечание: {notes}")
    return "\n".join(lines)


def _format_pricing_display(pricing: Dict[str, Any] | None) -> str:
    if not isinstance(pricing, dict):
        return ""
    amount = pricing.get("amount")
    if amount is None:
        return ""
    try:
        amount_value = int(amount)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return ""
    currency = str(pricing.get("currency") or "XTR").upper()
    currency_label = "XTR" if currency in {"XTR", "STARS"} else currency
    return f"{amount_value} {currency_label}"


def _make_idempotency_base(
    scope: str,
    *,
    user_id: int | None,
    attempt_id: int | None,
) -> str:
    """Build a deterministic idempotency base for user/attempt scoped flows."""

    if user_id is not None and attempt_id is not None:
        return f"bot:{scope}:{user_id}:{attempt_id}"
    return f"bot:{scope}:{uuid.uuid4().hex}"


def _idempotency_for(base: str, suffix: str) -> str:
    return f"{base}:{suffix}"


def _make_attempt_id() -> int:
    """Create a monotonic-ish identifier for plan payment attempts."""

    return int(time.time_ns() // 1_000_000)


async def _fetch_profile(backend: BackendClient, state: FSMContext, access: str | None, refresh: str | None) -> Dict[str, Any] | None:
    if not access:
        return None
    try:
        payload = await backend.get_me(access)
        return payload.get("profile") or {}
    except BackendAuthError:
        if not refresh:
            raise
        tokens = await backend.refresh_tokens(refresh)
        new_access = tokens.get("access")
        new_refresh = tokens.get("refresh") or refresh
        await state.update_data(access_token=new_access, refresh_token=new_refresh)
        if not new_access:
            raise BackendAuthError("Не удалось обновить доступ")
        payload = await backend.get_me(new_access)
        return payload.get("profile") or {}


async def _fetch_plan_pricing(
        backend: BackendClient,
        state: FSMContext,
        access: str | None,
        refresh: str | None,
) -> Dict[str, Any] | None:
    if not access:
        return None
    try:
        auth = await backend.get_wallet_pricing(access, refresh, action="generate_plan")
    except BackendValidationError:
        raise
    except BackendError:
        raise
    await _save_tokens(state, auth)
    pricing = auth.payload if isinstance(auth.payload, dict) else {}
    stars_blocked = bool(pricing.get("stars_purchase_blocked"))
    await state.update_data(
        plan_pricing=pricing,
        stars_purchase_blocked=stars_blocked,
    )
    return pricing


async def _consume_plan_hold(
        backend: BackendClient,
        state: FSMContext,
        access: str | None,
        refresh: str | None,
        hold_info: Dict[str, Any] | None,
        *,
        rid: str,
        telegram_user_id: int | None,
        attempt_id: int | None,
        action: str = PLAN_ACTION,
        message: Message | None = None,
) -> bool:
    hold_id = hold_info.get("id") if isinstance(hold_info, dict) else None
    if not hold_id:
        await state.update_data(plan_hold=None)
        return True

    key_base = str(
        hold_info.get("key_base")
        or _make_idempotency_base("plan", user_id=telegram_user_id, attempt_id=attempt_id)
    )
    consume_key = _idempotency_for(key_base, "consume")
    amount = hold_info.get("amount") if isinstance(hold_info, dict) else None
    currency = hold_info.get("currency") if isinstance(hold_info, dict) else None
    metadata: Dict[str, Any] = {
        "feature": "plan_generation",
        "action": action,
    }
    if attempt_id is not None:
        metadata["attempt_id"] = attempt_id

    try:
        auth = await backend.consume_wallet_hold(
            access,
            refresh,
            hold_id=int(hold_id),
            metadata=metadata,
            idempotency_key=consume_key,
        )
        await _save_tokens(state, auth)
        logger.info(
            "plan hold_consumed",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "hold_id": hold_id,
                "amount": amount,
                "currency": currency,
                "action": action,
                "idempotency_key": consume_key,
            },
        )
        return True
    except BackendError as exc:
        logger.error(
            "plan hold_consume_failed",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "hold_id": hold_id,
                "amount": amount,
                "currency": currency,
                "action": action,
                "idempotency_key": consume_key,
                "error": str(exc),
            },
        )
        if message is not None:
            await message.answer("Не удалось списать Stars за план. Попробуйте позже или обратитесь в поддержку.")
        return False
    finally:
        await state.update_data(plan_hold=None)


async def _release_plan_hold(
        backend: BackendClient,
        state: FSMContext,
        access: str | None,
        refresh: str | None,
        hold_info: Dict[str, Any] | None,
        *,
        rid: str,
        telegram_user_id: int | None,
        attempt_id: int | None,
        reason: str = "user_cancelled",
        action: str = PLAN_ACTION,
) -> None:
    hold_id = hold_info.get("id") if isinstance(hold_info, dict) else None
    if not hold_id:
        await state.update_data(plan_hold=None)
        return

    key_base = str(
        hold_info.get("key_base")
        or _make_idempotency_base("plan", user_id=telegram_user_id, attempt_id=attempt_id)
    )
    release_key = _idempotency_for(key_base, f"release:{reason}")
    amount = hold_info.get("amount") if isinstance(hold_info, dict) else None
    currency = hold_info.get("currency") if isinstance(hold_info, dict) else None
    metadata: Dict[str, Any] = {
        "feature": "plan_generation",
        "reason": reason,
        "action": action,
    }
    if attempt_id is not None:
        metadata["attempt_id"] = attempt_id

    try:
        await backend.release_wallet_hold(
            access,
            refresh,
            hold_id=int(hold_id),
            metadata=metadata,
            idempotency_key=release_key,
        )
        logger.info(
            "plan hold_released",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "hold_id": hold_id,
                "amount": amount,
                "currency": currency,
                "action": action,
                "reason": reason,
                "idempotency_key": release_key,
            },
        )
    except BackendError as exc:
        logger.warning(
            "plan hold_release_failed",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "hold_id": hold_id,
                "amount": amount,
                "currency": currency,
                "action": action,
                "reason": reason,
                "idempotency_key": release_key,
                "error": str(exc),
            },
        )
    finally:
        await state.update_data(plan_hold=None)


async def _handle_insufficient_balance(
        message: Message,
        state: FSMContext,
        pricing: Dict[str, Any] | None,
        period: int,
        *,
        attempt_id: int,
        rid: str,
        telegram_user_id: int | None,
        webapp_url: str | None,
        support_url: str | None,
) -> None:
    state_data = await state.get_data()

    amount_value: int | None = None
    currency_value: str | None = None
    if isinstance(pricing, dict):
        raw_amount = pricing.get("amount")
        try:
            amount_value = int(raw_amount) if raw_amount is not None else None
        except (TypeError, ValueError):
            amount_value = None
        raw_currency = pricing.get("currency")
        currency_value = str(raw_currency).upper() if raw_currency else None

    pending_action = {
        "type": PLAN_ACTION,
        "period": int(period),
        "amount": amount_value,
        "currency": currency_value or "XTR",
        "attempt_id": attempt_id,
        "status": "awaiting_payment",
    }
    await state.update_data(pending_action=pending_action)

    stars_blocked = bool(state_data.get("stars_purchase_blocked")) or bool(
        isinstance(pricing, dict) and pricing.get("stars_purchase_blocked")
    )
    if stars_blocked:
        await state.update_data(stars_purchase_blocked=True)
        await message.answer(
            STARS_BLOCKED_MESSAGE,
            reply_markup=plan_topup_keyboard(amounts=(), webapp_url=webapp_url, support_url=support_url),
        )
        logger.warning(
            "plan stars_blocked",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "amount": amount_value,
                "currency": currency_value or "XTR",
                "action": PLAN_ACTION,
            },
        )
        return

    amount_display = _format_pricing_display(pricing)
    if amount_display:
        text = f"Недостаточно Stars. Требуется {amount_display}. После пополнения продолжу автоматически."
    else:
        text = "Недостаточно Stars. После пополнения продолжу автоматически."

    await message.answer(
        text,
        reply_markup=plan_topup_keyboard(webapp_url=webapp_url, support_url=support_url),
    )
    logger.info(
        "plan insufficient_funds",
        extra={
            "rid": rid,
            "telegram_user_id": telegram_user_id,
            "attempt_id": attempt_id,
            "amount": amount_value,
            "currency": currency_value or "XTR",
            "action": PLAN_ACTION,
        },
    )


@router.callback_query(F.data.startswith("plan:topup:"))
async def plan_topup_callback(
        callback: CallbackQuery,
        state: FSMContext,
        provider_token: str | None,
        webapp_url: str | None,
        support_url: str | None = None,
):
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    data = await state.get_data()
    pending = data.get("pending_action") if isinstance(data.get("pending_action"), dict) else {}
    if pending.get("type") != PLAN_ACTION:
        await callback.answer("Нет ожидающих действий", show_alert=True)
        return

    try:
        amount_value = int(callback.data.split(":", 2)[-1])
    except (AttributeError, ValueError, IndexError):
        await callback.answer("Неизвестная сумма", show_alert=True)
        return

    stars_blocked = bool(data.get("stars_purchase_blocked"))
    if stars_blocked:
        await callback.message.answer(
            STARS_BLOCKED_MESSAGE,
            reply_markup=plan_topup_keyboard(amounts=(), webapp_url=webapp_url, support_url=support_url),
        )
        await callback.answer()
        return

    attempt_id = pending.get("attempt_id")
    try:
        attempt_int = int(attempt_id)
    except (TypeError, ValueError):
        await callback.answer("Попробуйте снова через меню плана", show_alert=True)
        return

    currency = str(pending.get("currency") or "XTR").upper()
    payload_extra = plan_topup_payload(data)
    if not payload_extra:
        payload_extra = {"intent": "plan_topup", "aid": str(attempt_int), "action": PLAN_ACTION}

    rid = get_request_id()
    logger.info(
        "plan quick_topup",
        extra={
            "rid": rid,
            "telegram_user_id": getattr(callback.from_user, "id", None),
            "amount": amount_value,
            "attempt_id": attempt_int,
            "currency": currency,
            "action": PLAN_ACTION,
        },
    )

    invoice = build_stars_topup_invoice(
        callback.from_user.id,
        amount_value,
        rid=rid,
        provider_token=provider_token,
        payload_extra=payload_extra,
    )
    await callback.message.answer_invoice(**invoice)

    updated_pending = {**pending, "status": "invoice_sent"}
    await state.update_data(pending_action=updated_pending)
    await callback.answer()


async def _initiate_plan_generation(
        *,
        backend: BackendClient,
        state: FSMContext,
        message: Message | None,
        access_token: str | None,
        refresh_token: str | None,
        period: int,
        pricing: Dict[str, Any] | None,
        rid: str,
        attempt_id: int,
        telegram_user_id: int | None,
        webapp_url: str | None = None,
        support_url: str | None = None,
) -> None:
    if not access_token or not refresh_token:
        if message:
            await message.edit_text("Авторизация истекла. Повторите вход через WebApp.")
        await _reset_state(state, keep_tokens=False)
        return

    if pricing is None:
        try:
            pricing = await _fetch_plan_pricing(backend, state, access_token, refresh_token)
        except BackendError as exc:
            if message:
                await message.edit_text("Не удалось получить стоимость генерации.\n" + str(exc))
            await _reset_state(state)
            return
    else:
        await state.update_data(plan_pricing=pricing)

    hold_info: Dict[str, Any] | None = None
    hold_key_base = _make_idempotency_base("plan", user_id=telegram_user_id, attempt_id=attempt_id)
    hold_key = _idempotency_for(hold_key_base, "hold")
    hold_context = {"period_days": int(period), "attempt_id": attempt_id}
    hold_metadata: Dict[str, Any] = {
        "feature": "plan_generation",
        "action": PLAN_ACTION,
        "period_days": int(period),
        "attempt_id": attempt_id,
    }
    if telegram_user_id is not None:
        hold_metadata["telegram_user_id"] = telegram_user_id
    raw_amount = pricing.get("amount") if isinstance(pricing, dict) else None
    try:
        amount_value = int(raw_amount) if raw_amount is not None else None
    except (TypeError, ValueError):
        amount_value = None
    raw_currency = pricing.get("currency") if isinstance(pricing, dict) else None
    currency_value = str(raw_currency).upper() if raw_currency else "XTR"
    try:
        hold_auth = await backend.create_wallet_hold(
            access_token,
            refresh_token,
            action=PLAN_ACTION,
            amount=int(amount_value or 0),
            currency=raw_currency,
            metadata=hold_metadata,
            context=hold_context,
            idempotency_key=hold_key,
        )
        await _save_tokens(state, hold_auth)
        payload = hold_auth.payload if isinstance(hold_auth.payload, dict) else {}
        hold_info = {
            "id": payload.get("id"),
            "amount": payload.get("amount"),
            "currency": payload.get("currency"),
            "key_base": hold_key_base,
            "context": hold_context,
            "attempt_id": attempt_id,
            "action": PLAN_ACTION,
            "telegram_user_id": telegram_user_id,
        }
        await state.update_data(plan_hold=hold_info)
        logger.info(
            "plan hold_created",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "hold_id": hold_info.get("id"),
                "amount": hold_info.get("amount"),
                "currency": hold_info.get("currency"),
                "action": PLAN_ACTION,
                "idempotency_key": hold_key,
            },
        )
    except BackendValidationError as exc:
        details = exc.errors if isinstance(exc.errors, dict) else {}
        code = details.get("code") if isinstance(details, dict) else None
        stars_blocked = bool(details.get("stars_purchase_blocked")) if isinstance(details, dict) else False
        if stars_blocked:
            await state.update_data(stars_purchase_blocked=True)
        if code == "insufficient_funds":
            if message:
                await _handle_insufficient_balance(
                    message,
                    state,
                    pricing,
                    period,
                    attempt_id=attempt_id,
                    rid=rid,
                    telegram_user_id=telegram_user_id,
                    webapp_url=webapp_url,
                    support_url=support_url,
                )
            return
        if stars_blocked and message:
            await message.edit_text(STARS_BLOCKED_MESSAGE)
            await state.update_data(plan_hold=None)
            return
        message_text = str(details.get("detail") or details)
        if message:
            await message.edit_text("Не удалось зарезервировать Stars.\n" + message_text)
        await state.update_data(plan_hold=None)
        return
    except BackendError as exc:
        if message:
            await message.edit_text("Не удалось зарезервировать Stars.\n" + str(exc))
        logger.error(
            "plan hold_create_failed",
            extra={
                "rid": rid,
                "telegram_user_id": telegram_user_id,
                "attempt_id": attempt_id,
                "amount": amount_value,
                "currency": currency_value,
                "action": PLAN_ACTION,
                "idempotency_key": hold_key,
                "error": str(exc),
            },
        )
        await state.update_data(plan_hold=None)
        return

    access = hold_auth.access or access_token
    refresh = hold_auth.refresh or refresh_token
    if message:
        await message.edit_text("Stars зарезервированы, запускаю генерацию…")
    payload = {"period_days": int(period)}
    try:
        auth = await backend.generate_plan(access, refresh, payload)
    except BackendValidationError as exc:
        if message:
            await message.edit_text("Проверьте введённые параметры.\n" + f"{exc.errors}")
        await _release_plan_hold(
            backend,
            state,
            access,
            refresh,
            hold_info,
            rid=rid,
            telegram_user_id=telegram_user_id,
            attempt_id=attempt_id,
            reason="validation_failed",
        )
        await _reset_state(state)
        return
    except BackendAuthError:
        if message:
            await message.edit_text("Авторизация истекла. Повторите вход через WebApp.")
        await _release_plan_hold(
            backend,
            state,
            access,
            refresh,
            hold_info,
            rid=rid,
            telegram_user_id=telegram_user_id,
            attempt_id=attempt_id,
            reason="auth_failed",
        )
        await _reset_state(state, keep_tokens=False)
        return
    except BackendError as exc:
        if message:
            await message.edit_text("Не удалось запустить генерацию.\n" + str(exc))
        await _release_plan_hold(
            backend,
            state,
            access,
            refresh,
            hold_info,
            rid=rid,
            telegram_user_id=telegram_user_id,
            attempt_id=attempt_id,
            reason="engine_failed",
        )
        await _reset_state(state)
        return

    await _save_tokens(state, auth)
    result = auth.payload or {}
    access = auth.access or access
    refresh = auth.refresh or refresh
    if "job_id" in result:
        await state.set_state(PlanGeneration.awaiting_job)
        await state.update_data(
            plan_job_id=result["job_id"],
            plan_pricing=pricing,
            plan_hold=hold_info,
            plan_period=period,
            pending_action={
                "type": PLAN_ACTION,
                "period": int(period),
                "amount": amount_value,
                "currency": currency_value,
                "attempt_id": attempt_id,
                "status": "processing",
            },
        )
        if message:
            await message.edit_text("Генерирую план… это может занять пару секунд ⏳")
            await _poll_job_status(
                message,
                backend,
                state,
                access,
                refresh,
                result["job_id"],
                hold_info=hold_info,
                pricing=pricing,
                rid=rid,
                telegram_user_id=telegram_user_id,
                attempt_id=attempt_id,
            )
        return

    plan_id = result.get("plan_id")
    summary = result.get("summary") or {}
    if not plan_id:
        if message:
            await message.edit_text("Не удалось построить план. Попробуйте ещё раз позже.")
        await _release_plan_hold(
            backend,
            state,
            access,
            refresh,
            hold_info,
            rid=rid,
            telegram_user_id=telegram_user_id,
            attempt_id=attempt_id,
            reason="engine_failed",
        )
        await _reset_state(state)
        return

    consumed = await _consume_plan_hold(
        backend,
        state,
        access,
        refresh,
        hold_info,
        rid=rid,
        telegram_user_id=telegram_user_id,
        attempt_id=attempt_id,
        action=PLAN_ACTION,
        message=message,
    )
    if not consumed:
        await _reset_state(state)
        return
    if message:
        await _render_plan_ready(message, int(plan_id), summary, state, pricing)


@router.message(Command("plan"))
async def plan_command(message: Message, backend: BackendClient, state: FSMContext, access_token: str | None):
    data = await state.get_data()
    refresh_token = data.get("refresh_token")
    if not access_token or not refresh_token:
        await message.answer("Сначала авторизуйтесь через WebApp и заполните профиль (команда /profile).")
        return

    try:
        profile = await _fetch_profile(backend, state, access_token, refresh_token)
    except BackendError as exc:
        await message.answer("Не удалось получить профиль. Попробуйте позже." + f"\n{exc}")
        return

    if profile is None:
        await message.answer("Профиль не найден. Завершите анкету через /profile.")
        return

    await state.update_data(plan_profile=profile)
    pricing: Dict[str, Any] | None = None
    try:
        pricing = await _fetch_plan_pricing(backend, state, access_token, refresh_token)
    except BackendError as exc:
        await message.answer("Не удалось получить стоимость генерации.\n" + str(exc))
        return
    await state.set_state(PlanGeneration.choosing_period)
    hint_lines = [_format_profile_hint(profile)]
    pricing_display = _format_pricing_display(pricing)
    if pricing_display:
        hint_lines.append(f"\nСтоимость генерации: {pricing_display}")
    hint_lines.append("\nВыберите период плана:")
    await message.answer("\n".join(hint_lines), reply_markup=period_keyboard())


@router.callback_query(PlanGeneration.choosing_period, F.data.startswith("plan:period:"))
async def choose_period(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        period = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.message.answer("Некорректный период.")
        return
    await state.update_data(plan_period=period)
    await callback.message.edit_text(
        f"Период: {period} дней.\nНажмите, чтобы запустить генерацию.",
        reply_markup=generate_keyboard(),
    )


@router.callback_query(F.data == "plan:cancel")
async def cancel_plan(callback: CallbackQuery, backend: BackendClient, state: FSMContext):
    await callback.answer("Отменено")
    data = await state.get_data()
    hold_info = data.get("plan_hold") if isinstance(data.get("plan_hold"), dict) else None
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    rid = get_request_id()
    telegram_user_id = getattr(callback.from_user, "id", None)
    attempt_value = None
    if isinstance(hold_info, dict):
        attempt_value = hold_info.get("attempt_id")
        try:
            attempt_value = int(attempt_value) if attempt_value is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            attempt_value = None
    if hold_info and access_token and refresh_token:
        await _release_plan_hold(
            backend,
            state,
            access_token,
            refresh_token,
            hold_info,
            rid=rid,
            telegram_user_id=telegram_user_id,
            attempt_id=attempt_value,
            reason="user_cancelled",
        )
    else:
        await state.update_data(plan_hold=None)
    await _reset_state(state)
    if callback.message:
        await callback.message.edit_text("Операция отменена.")


async def _render_plan_ready(
    message: Message,
    plan_id: int,
    summary: Dict[str, Any],
    state: FSMContext,
    pricing: Dict[str, Any] | None,
) -> None:
    await _reset_state(state)
    lines = ["План готов!"]
    pricing_display = _format_pricing_display(pricing)
    if pricing_display:
        lines.append(f"Списано: {pricing_display}")
    lines.append(_format_plan_summary(summary))
    await message.edit_text(
        "\n\n".join(lines),
        reply_markup=summary_actions_keyboard(plan_id, int(summary.get("daily_kcal") or 0)),
    )


async def _poll_job_status(
        message: Message,
        backend: BackendClient,
        state: FSMContext,
        access_token: str | None,
        refresh_token: str | None,
        job_id: str,
        *,
        hold_info: Dict[str, Any] | None,
        pricing: Dict[str, Any] | None,
        rid: str,
        telegram_user_id: int | None,
        attempt_id: int | None,
        action: str = PLAN_ACTION,
) -> None:
    delay = 1.0
    hold_id = hold_info.get("id") if isinstance(hold_info, dict) else None
    logger.info(
        "plan job_poll_start",
        extra={
            "rid": rid,
            "telegram_user_id": telegram_user_id,
            "attempt_id": attempt_id,
            "job_id": job_id,
            "hold_id": hold_id,
            "action": action,
        },
    )
    for attempt in range(6):
        await asyncio.sleep(delay)
        try:
            auth = await backend.job_status(access_token, refresh_token, job_id)
        except BackendError as exc:
            await message.edit_text("Не удалось получить статус генерации." + f"\n{exc}")
            await _release_plan_hold(
                backend,
                state,
                access_token,
                refresh_token,
                hold_info,
                rid=rid,
                telegram_user_id=telegram_user_id,
                attempt_id=attempt_id,
                reason="job_failed",
            )
            logger.error(
                "plan job_failed",
                extra={
                    "rid": rid,
                    "telegram_user_id": telegram_user_id,
                    "attempt_id": attempt_id,
                    "job_id": job_id,
                    "hold_id": hold_id,
                    "action": action,
                    "error": str(exc),
                },
            )
            await _reset_state(state)
            return
        await _save_tokens(state, auth)
        payload = auth.payload or {}
        status = payload.get("status")
        if status in {"PENDING", "pending"}:
            delay = min(delay * 1.6, 10.0)
            await message.edit_text(f"Генерирую план… ({attempt + 1}/6)")
            access_token = auth.access
            refresh_token = auth.refresh
            continue
        if status == "failed":
            error = payload.get("error") or "Неизвестная ошибка"
            await message.edit_text("Не удалось построить план. " + error)
            await _release_plan_hold(
                backend,
                state,
                auth.access or access_token,
                auth.refresh or refresh_token,
                hold_info,
                rid=rid,
                telegram_user_id=telegram_user_id,
                attempt_id=attempt_id,
                reason="job_failed",
            )
            logger.error(
                "plan job_failed",
                extra={
                    "rid": rid,
                    "telegram_user_id": telegram_user_id,
                    "attempt_id": attempt_id,
                    "job_id": job_id,
                    "hold_id": hold_id,
                    "action": action,
                    "error": str(error),
                },
            )
            await _reset_state(state)
            return
        if status == "done":
            plan_id = payload.get("plan_id")
            summary = payload.get("summary") or {}
            consumed = await _consume_plan_hold(
                backend,
                state,
                auth.access or access_token,
                auth.refresh or refresh_token,
                hold_info,
                rid=rid,
                telegram_user_id=telegram_user_id,
                attempt_id=attempt_id,
                action=action,
                message=message,
            )
            if not consumed:
                await _reset_state(state)
                return
            logger.info(
                "plan job_completed",
                extra={
                    "rid": rid,
                    "telegram_user_id": telegram_user_id,
                    "attempt_id": attempt_id,
                    "job_id": job_id,
                    "hold_id": hold_id,
                    "action": action,
                },
            )
            await _render_plan_ready(message, int(plan_id), summary, state, pricing)
            return
    await message.edit_text("Подготовка плана занимает слишком много времени. Попробуйте чуть позже.")
    await _release_plan_hold(
        backend,
        state,
        access_token,
        refresh_token,
        hold_info,
        rid=rid,
        telegram_user_id=telegram_user_id,
        attempt_id=attempt_id,
        reason="job_timeout",
    )
    logger.error(
        "plan job_timeout",
        extra={
            "rid": rid,
            "telegram_user_id": telegram_user_id,
            "attempt_id": attempt_id,
            "job_id": job_id,
            "hold_id": hold_id,
            "action": action,
        },
    )
    await _reset_state(state)


@router.callback_query(F.data == "plan:generate")
async def generate_plan(
        callback: CallbackQuery,
        backend: BackendClient,
        state: FSMContext,
        webapp_url: str | None,
        support_url: str | None = None,
):
    await callback.answer()
    data = await state.get_data()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    try:
        period = int(data.get("plan_period") or 7)
    except (TypeError, ValueError):
        period = 7
    pricing: Dict[str, Any] | None = data.get("plan_pricing") if isinstance(data.get("plan_pricing"), dict) else None
    rid = get_request_id()
    await state.update_data(pending_action=None)
    attempt_id = _make_attempt_id()
    telegram_user_id = getattr(callback.from_user, "id", None)
    await _initiate_plan_generation(
        backend=backend,
        state=state,
        message=callback.message,
        access_token=access_token,
        refresh_token=refresh_token,
        period=period,
        pricing=pricing,
        rid=rid,
        attempt_id=attempt_id,
        telegram_user_id=telegram_user_id,
        webapp_url=webapp_url,
        support_url=support_url,
    )


async def resume_plan_generation_if_needed(
        message: Message,
        backend: BackendClient,
        state: FSMContext,
        *,
        rid: str,
        attempt_id: int | None = None,
        intent: str | None = None,
        webapp_url: str | None = None,
        support_url: str | None = None,
) -> bool:
    data = await state.get_data()
    pending = data.get("pending_action")
    if not isinstance(pending, dict) or pending.get("type") != "generate_plan":
        return False

    stored_attempt = pending.get("attempt_id")
    stored_attempt_int: int | None = None
    if stored_attempt is not None:
        try:
            stored_attempt_int = int(stored_attempt)
        except (TypeError, ValueError):
            return False
        if attempt_id is not None and stored_attempt_int != attempt_id:
            return False
    elif attempt_id is not None:
        return False

    if attempt_id is not None and intent and intent != "plan_topup":
        return False

    status = str(pending.get("status") or "awaiting_payment")
    if status not in {"awaiting_payment", "invoice_sent", "payment_confirmed"}:
        return False

    try:
        period = int(pending.get("period"))
    except (TypeError, ValueError):
        period = data.get("plan_period")
    try:
        period_value = int(period or 7)
    except (TypeError, ValueError):
        period_value = 7

    await state.update_data(pending_action=None)
    telegram_user_id = getattr(message.from_user, "id", None)
    logger.info(
        "plan resume_after_payment",
        extra={
            "rid": rid,
            "telegram_user_id": telegram_user_id,
            "period": period_value,
            "attempt_id": stored_attempt_int if stored_attempt_int is not None else attempt_id,
        },
    )

    progress_message = await message.answer("Оплата получена! Продолжаю генерацию плана…")
    target_message = progress_message if hasattr(progress_message, "edit_text") else message
    pricing: Dict[str, Any] | None = data.get("plan_pricing") if isinstance(data.get("plan_pricing"), dict) else None
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    await _initiate_plan_generation(
        backend=backend,
        state=state,
        message=target_message,
        access_token=access_token,
        refresh_token=refresh_token,
        period=period_value,
        pricing=pricing,
        rid=rid,
        attempt_id=stored_attempt_int if stored_attempt_int is not None else (attempt_id or _make_attempt_id()),
        telegram_user_id=telegram_user_id,
        webapp_url=webapp_url,
        support_url=support_url,
    )
    return True


@router.message(Command("history"))
async def history_command(message: Message, backend: BackendClient, state: FSMContext, access_token: str | None):
    data = await state.get_data()
    refresh_token = data.get("refresh_token")
    if not access_token or not refresh_token:
        await message.answer("История доступна после авторизации через WebApp.")
        return
    try:
        auth = await backend.get_history(access_token, refresh_token, limit=5)
    except BackendAuthError:
        await message.answer("Авторизация истекла. Перейдите в /plan после обновления токена.")
        await _reset_state(state, keep_tokens=False)
        return
    except BackendError as exc:
        await message.answer("Не удалось получить историю." + f"\n{exc}")
        return
    await _save_tokens(state, auth)
    plans = auth.payload if isinstance(auth.payload, list) else []
    if not plans:
        await message.answer("Пока нет сгенерированных планов.")
        return
    lines = []
    for entry in plans:
        summary = entry.get("summary") or {}
        cost = summary.get("estimated_cost_rub_per_day", "—")
        lines.append(
            f"#{entry.get('plan_id')} — {summary.get('daily_kcal', '—')} ккал, {cost} ₽/день"
        )
    await message.answer("История планов:\n" + "\n".join(lines))


@router.callback_query(F.data.startswith("plan:accept:"))
async def accept_plan_callback(callback: CallbackQuery, backend: BackendClient, state: FSMContext):
    await callback.answer()
    plan_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    try:
        auth = await backend.accept_plan(data.get("access_token"), data.get("refresh_token"), plan_id)
    except BackendError as exc:
        await callback.message.answer("Не удалось принять план." + f"\n{exc}")
        return
    await _save_tokens(state, auth)
    await callback.message.edit_text(
        "План принят ✅\n" + _format_plan_summary(auth.payload.get("summary") or {}),
    )


@router.callback_query(F.data.startswith("plan:reject:"))
async def reject_plan_callback(callback: CallbackQuery, backend: BackendClient, state: FSMContext):
    await callback.answer()
    plan_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    try:
        auth = await backend.reject_plan(data.get("access_token"), data.get("refresh_token"), plan_id)
    except BackendError as exc:
        await callback.message.answer("Не удалось отклонить план." + f"\n{exc}")
        return
    await _save_tokens(state, auth)
    await callback.message.edit_text(
        "План отклонён. Хотите пересчитать?",
        reply_markup=summary_actions_keyboard(plan_id, int(auth.payload.get("summary", {}).get("daily_kcal") or 0)),
    )


@router.callback_query(F.data.startswith("plan:regen:"))
async def regenerate_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    try:
        plan_id = int(parts[2])
        daily_kcal = int(parts[3])
    except (IndexError, ValueError):
        await callback.message.answer("Не удалось подготовить пересчёт.")
        return
    await state.set_state(PlanGeneration.awaiting_regen_choice)
    await state.update_data(regen_plan_id=plan_id, regen_kcal=daily_kcal)
    await callback.message.edit_text(
        "Как скорректировать калорийность?",
        reply_markup=regeneration_options_keyboard(plan_id, daily_kcal),
    )


@router.callback_query(F.data.startswith("plan:regen_adjust:"))
async def regenerate_execute(callback: CallbackQuery, backend: BackendClient, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    try:
        plan_id = int(parts[2])
        mode = parts[3]
        base = int(parts[4])
    except (IndexError, ValueError):
        await callback.message.answer("Некорректные параметры пересчёта.")
        await _reset_state(state)
        return

    factor = {"less": 0.9, "more": 1.1, "same": 1.0}.get(mode, 1.0)
    target = max(800, int(round(base * factor / 10.0) * 10))

    data = await state.get_data()
    try:
        auth = await backend.regenerate_plan(
            data.get("access_token"),
            data.get("refresh_token"),
            plan_id,
            overrides={"target_calories": target},
        )
    except BackendValidationError as exc:
        await callback.message.answer("Пересчёт невозможен: " + str(exc.errors))
        await _reset_state(state)
        return
    except BackendError as exc:
        await callback.message.answer("Не удалось пересчитать план." + f"\n{exc}")
        await _reset_state(state)
        return

    await _save_tokens(state, auth)
    summary = auth.payload.get("summary") or {}
    await _reset_state(state)
    await callback.message.edit_text(
        "Обновлённый план готов ✅\n" + _format_plan_summary(summary),
        reply_markup=summary_actions_keyboard(auth.payload.get("plan_id"), int(summary.get("daily_kcal") or target)),
    )


@router.callback_query(F.data == "plan:regen_cancel")
async def regenerate_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Отмена")
    await _reset_state(state)
    await callback.message.edit_text("Пересчёт отменён.")