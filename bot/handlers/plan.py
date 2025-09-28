"""Handlers for nutrition plan flow."""
from __future__ import annotations

import asyncio
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
from bot.keyboards.plan import (
    generate_keyboard,
    period_keyboard,
    regeneration_options_keyboard,
    summary_actions_keyboard,
)
from bot.states import PlanGeneration

router = Router()


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
    await state.set_state(PlanGeneration.choosing_period)
    await message.answer(
        _format_profile_hint(profile) + "\n\nВыберите период плана:",
        reply_markup=period_keyboard(),
    )


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
async def cancel_plan(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    await _reset_state(state)
    if callback.message:
        await callback.message.edit_text("Операция отменена.")


async def _handle_generation_result(
    message: Message,
    result: Dict[str, Any],
    state: FSMContext,
) -> None:
    if "job_id" in result:
    await state.set_state(PlanGeneration.awaiting_job)
    await state.update_data(plan_job_id=result["job_id"])
    await message.edit_text("Генерирую план… это может занять пару секунд ⏳")
    return

    plan_id = result.get("plan_id")
    summary = result.get("summary") or {}
    await _reset_state(state)
    await message.edit_text(
        "План готов!\n" + _format_plan_summary(summary),
        reply_markup=summary_actions_keyboard(plan_id, int(summary.get("daily_kcal") or 0)),
    )


async def _poll_job_status(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    refresh_token: str | None,
    job_id: str,
) -> None:
    delay = 1.0
    for attempt in range(6):
        await asyncio.sleep(delay)
        try:
            auth = await backend.job_status(access_token, refresh_token, job_id)
        except BackendError as exc:
            await message.edit_text("Не удалось получить статус генерации." + f"\n{exc}")
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
            await _reset_state(state)
            return
        if status == "done":
            plan_id = payload.get("plan_id")
            summary = payload.get("summary") or {}
            await _reset_state(state)
            await message.edit_text(
                "План готов!\n" + _format_plan_summary(summary),
                reply_markup=summary_actions_keyboard(plan_id, int(summary.get("daily_kcal") or 0)),
            )
            return
    await message.edit_text("Подготовка плана занимает слишком много времени. Попробуйте чуть позже.")
    await _reset_state(state)


@router.callback_query(F.data == "plan:generate")
async def generate_plan(callback: CallbackQuery, backend: BackendClient, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    period = int(data.get("plan_period", 7))
    payload = {"period_days": period}

    try:
        auth = await backend.generate_plan(access_token, refresh_token, payload)
    except BackendValidationError as exc:
        await callback.message.edit_text("Проверьте введённые параметры." + f"\n{exc.errors}")
        await _reset_state(state)
        return
    except BackendAuthError:
        await callback.message.edit_text("Авторизация истекла. Повторите вход через WebApp.")
        await _reset_state(state, keep_tokens=False)
        return
    except BackendError as exc:
        await callback.message.edit_text("Не удалось запустить генерацию." + f"\n{exc}")
        await _reset_state(state)
        return

    await _save_tokens(state, auth)
    await _handle_generation_result(callback.message, auth.payload, state)
    if "job_id" in auth.payload:
        await _poll_job_status(
            callback.message,
            backend,
            state,
            auth.access,
            auth.refresh,
            auth.payload["job_id"],
        )


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