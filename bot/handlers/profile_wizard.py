from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.backend_client import (
    BackendAuthError,
    BackendClient,
    BackendError,
    BackendValidationError,
)
from bot.constants import STARS_BLOCKED_MESSAGE
from bot.logkit import get_request_id
from bot.states import ProfileWizard
from .wallet import (
    _authorization_keyboard,
    _get_tokens,
    build_stars_topup_invoice,
    plan_topup_payload,
)

router = Router()

ALLERGY_OPTIONS = [
    ("nuts", "Орехи"),
    ("gluten", "Глютен"),
    ("lactose", "Лактоза"),
    ("eggs", "Яйца"),
    ("soy", "Соя"),
    ("seafood", "Морепродукты"),
]
ALLERGY_LABELS = {value: label for value, label in ALLERGY_OPTIONS}

GOAL_OPTIONS = [
    ("lose_weight", "Снижение веса"),
    ("gain_muscle", "Набрать мышечную массу"),
    ("keep_fit", "Поддерживать форму"),
]
GOAL_LABELS = {value: label for value, label in GOAL_OPTIONS}


def _build_authorization_markup(webapp_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if webapp_url.lower().startswith("https://"):
        builder.button(text="Открыть анкету", web_app=WebAppInfo(url=webapp_url))
    else:
        builder.button(text="Открыть анкету", url=webapp_url)
    builder.adjust(1)
    return builder.as_markup()


def _build_allergy_keyboard(selected: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in ALLERGY_OPTIONS:
        prefix = "✅" if value in selected else "▫️"
        builder.button(text=f"{prefix} {label}", callback_data=f"allergy:{value}")
    builder.button(text="Готово", callback_data="allergy:done")
    builder.button(text="Очистить", callback_data="allergy:clear")
    builder.button(text="Отмена", callback_data="wizard:cancel")
    builder.adjust(2)
    return builder.as_markup()


def _build_goal_keyboard(selected: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in GOAL_OPTIONS:
        prefix = "✅" if value == selected else "▫️"
        builder.button(text=f"{prefix} {label}", callback_data=f"goal:{value}")
    builder.button(text="Отмена", callback_data="wizard:cancel")
    builder.adjust(1)
    return builder.as_markup()


def _build_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сохранить", callback_data="profile:save")
    builder.button(text="Отмена", callback_data="profile:cancel")
    builder.adjust(1)
    return builder.as_markup()


def _format_budget(value: Decimal | None) -> str:
    if value is None:
        return "Не указан"
    return f"{value.quantize(Decimal('0.01'))} ₽"


def _format_allergies(values: List[str]) -> str:
    if not values:
        return "Нет"
    labels = [ALLERGY_LABELS.get(v, v) for v in values]
    return ", ".join(labels)


def _format_goal(value: str | None) -> str:
    return GOAL_LABELS.get(value or "keep_fit", "Поддерживать форму")


def _extract_budget(raw: Any) -> Decimal | None:
    if raw in (None, "", []):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


async def _update_form(state: FSMContext, **updates: Any) -> Dict[str, Any]:
    data = await state.get_data()
    form = dict(data.get("profile_form") or {})
    form.update(updates)
    await state.update_data(profile_form=form)
    return form


async def _get_form(state: FSMContext) -> Dict[str, Any]:
    data = await state.get_data()
    return dict(data.get("profile_form") or {})


async def _start_profile_flow(
        message: Message,
        backend: BackendClient,
        state: FSMContext,
        access_token: str | None,
        webapp_url: str,
) -> None:
    if not access_token:
        await state.clear()
        await message.answer(
            "Сначала авторизуйтесь через WebApp, затем повторите попытку.",
            reply_markup=_build_authorization_markup(webapp_url),
        )
        return

    try:
        payload = await backend.get_me(access_token)
    except BackendAuthError:
        await state.update_data(access_token=None)
        await message.answer(
            "Сессия истекла. Авторизуйтесь заново через кнопку ниже.",
            reply_markup=_build_authorization_markup(webapp_url),
        )
        return
    except BackendError as exc:
        await message.answer(
            "Не удалось загрузить профиль. Попробуйте позже." + f"\n{exc}",
        )
        return

    profile = payload.get("profile", {})
    form = {
        "city": profile.get("city") or "",
        "budget": _extract_budget(profile.get("budget")),
        "allergies": list(profile.get("allergies", [])),
        "goals": profile.get("goals") or "keep_fit",
    }
    await state.update_data(profile_form=form, profile_payload=payload)

    city_hint = f" (текущее значение: {form['city']})" if form["city"] else ""
    await state.set_state(ProfileWizard.city)
    await message.answer(
        "В каком городе вы находитесь?" + city_hint,
    )


@router.message(Command("profile"))
async def on_profile_command(
        message: Message,
        backend: BackendClient,
        state: FSMContext,
        access_token: str | None,
        webapp_url: str,
):
    await _start_profile_flow(message, backend, state, access_token, webapp_url)


@router.callback_query(F.data == "wizard:start")
async def on_wizard_start(
    callback: CallbackQuery,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
    webapp_url: str,
):
    await callback.answer()
    if callback.message:
        await _start_profile_flow(
            callback.message, backend, state, access_token, webapp_url
        )


@router.message(ProfileWizard.city)
async def wizard_city(message: Message, state: FSMContext):
    city = (message.text or "").strip()
    if len(city) < 2:
        await message.answer("Введите название города полностью.")
        return

    await _update_form(state, city=city)
    form = await _get_form(state)
    current_budget = _format_budget(form.get("budget"))
    await state.set_state(ProfileWizard.budget)
    await message.answer(
        "Каков ваш дневной бюджет на питание в ₽?\n"
        f"Текущее значение: {current_budget}",
    )


@router.message(ProfileWizard.budget)
async def wizard_budget(message: Message, state: FSMContext):
    raw = (message.text or "").replace(",", ".").strip()
    try:
        budget = Decimal(raw)
    except (InvalidOperation, ValueError):
        await message.answer("Не удалось распознать число. Пример: 1500.00")
        return
    if budget < 0:
        await message.answer("Бюджет не может быть отрицательным.")
        return

    await _update_form(state, budget=budget)
    form = await _get_form(state)
    await state.set_state(ProfileWizard.allergies)
    await message.answer(
        "Выберите аллергии. Нажимайте на кнопки, затем — 'Готово'.",
        reply_markup=_build_allergy_keyboard(form.get("allergies", [])),
    )


@router.callback_query(ProfileWizard.allergies, F.data.startswith("allergy:"))
async def wizard_allergies(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]
    form = await _get_form(state)
    selected = list(form.get("allergies", []))

    if action == "done":
        await callback.answer()
        await state.set_state(ProfileWizard.goals)
        await callback.message.edit_reply_markup()
        await callback.message.answer(
            "Выберите свою цель:",
            reply_markup=_build_goal_keyboard(form.get("goals")),
        )
        return

    if action == "clear":
        selected = []
        await callback.answer("Список очищен")
    else:
        if action in selected:
            selected.remove(action)
        else:
            selected.append(action)
        await callback.answer()

    await _update_form(state, allergies=selected)
    await callback.message.edit_reply_markup(
        reply_markup=_build_allergy_keyboard(selected)
    )


@router.callback_query(ProfileWizard.goals, F.data.startswith("goal:"))
async def wizard_goal(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await _update_form(state, goals=value)
    form = await _get_form(state)
    await state.set_state(ProfileWizard.confirm)
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "Проверьте данные и подтвердите сохранение:\n" + _format_summary(form),
        reply_markup=_build_confirmation_keyboard(),
    )


def _format_summary(form: Dict[str, Any]) -> str:
    city = form.get("city") or "Не указан"
    budget = _format_budget(form.get("budget"))
    allergies = _format_allergies(form.get("allergies", []))
    goal = _format_goal(form.get("goals"))
    return (
        f"<b>Город:</b> {city}\n"
        f"<b>Бюджет:</b> {budget}\n"
        f"<b>Аллергии:</b> {allergies}\n"
        f"<b>Цель:</b> {goal}"
    )


def _prepare_payload(form: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "city": form.get("city", ""),
        "allergies": form.get("allergies", []),
        "goals": form.get("goals", "keep_fit"),
    }
    budget = form.get("budget")
    if isinstance(budget, Decimal):
        payload["budget"] = str(budget.quantize(Decimal("0.01")))
    elif budget in (None, ""):
        payload["budget"] = None
    else:
        payload["budget"] = str(budget)
    return payload


def _first_validation_error(errors: Dict[str, Any]) -> str:
    for field, detail in errors.items():
        if isinstance(detail, (list, tuple)) and detail:
            return f"{field}: {detail[0]}"
        if isinstance(detail, dict):
            for sub_detail in detail.values():
                if isinstance(sub_detail, (list, tuple)) and sub_detail:
                    return f"{field}: {sub_detail[0]}"
        if detail:
            return f"{field}: {detail}"
    return "Проверьте введённые данные"


@router.callback_query(ProfileWizard.confirm, F.data == "profile:save")
async def wizard_save(
    callback: CallbackQuery,
    backend: BackendClient,
    state: FSMContext,
    access_token: str | None,
):
    await callback.answer()
    form = await _get_form(state)
    if not access_token:
        await callback.message.answer(
            "Токен доступа потерян. Авторизуйтесь заново командой /profile."
        )
        await state.clear()
        return

    payload = _prepare_payload(form)

    try:
        result = await backend.upsert_profile(access_token, payload)
    except BackendValidationError as exc:
        await callback.message.answer(
            "Не удалось сохранить профиль: " + _first_validation_error(exc.errors)
        )
        return
    except BackendAuthError:
        await state.update_data(access_token=None)
        await callback.message.answer(
            "Авторизация недействительна. Попробуйте снова через /profile."
        )
        await state.clear()
        return
    except BackendError as exc:
        await callback.message.answer(
            "Не удалось сохранить профиль. Попробуйте позже." + f"\n{exc}"
        )
        return

    await state.clear()
    await callback.message.edit_reply_markup()
    profile = result.get("profile", {})
    summary = _format_summary(
        {
            "city": profile.get("city"),
            "budget": _extract_budget(profile.get("budget")),
            "allergies": profile.get("allergies", []),
            "goals": profile.get("goals"),
        }
    )
    await callback.message.answer("Профиль обновлён ✅\n" + summary)


@router.callback_query(ProfileWizard.confirm, F.data == "profile:cancel")
@router.callback_query(F.data == "wizard:cancel")
async def wizard_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup()
    await callback.message.answer("Обновление профиля отменено.")


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Действие отменено.")


@router.message(F.web_app_data)
async def webapp_credentials(
    message: Message,
    backend: BackendClient,
    state: FSMContext,
    webapp_url: str,
    provider_token: str | None,
):
    raw = message.web_app_data.data if message.web_app_data else ""
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"init_data": raw}
    access_token = str(parsed.get("access_token") or "").strip()
    if access_token:
        updates = {"access_token": access_token}
        refresh_token = parsed.get("refresh_token")
        if isinstance(refresh_token, str) and refresh_token:
            updates["refresh_token"] = refresh_token
        await state.update_data(**updates)
        await message.answer("Сессия WebApp обновлена — можно использовать /wallet для пополнения Stars.")
        return

    if parsed.get("action") == "topup":
        if message.from_user is None:
            await message.answer("Не удалось определить пользователя Telegram для счета.")
            return
        try:
            amount = int(parsed.get("amount"))
        except (TypeError, ValueError):
            await message.answer("Сумма пополнения указана неверно.")
            return
        if amount <= 0:
            await message.answer("Сумма пополнения должна быть положительной.")
            return
        stored_access_token, _ = await _get_tokens(state, None)
        if not stored_access_token:
            await message.answer(
                "Сначала авторизуйтесь через WebApp, чтобы пополнять баланс.",
                reply_markup=_authorization_keyboard(webapp_url),
            )
            return
        state_data = await state.get_data()
        if state_data.get("stars_purchase_blocked"):
            await message.answer(
                STARS_BLOCKED_MESSAGE
            )
            return
        invoice = build_stars_topup_invoice(
            message.from_user.id,
            amount,
            comment="Пополнение через WebApp",
            rid=get_request_id(),
            provider_token=provider_token,
            payload_extra=plan_topup_payload(state_data),
        )
        await message.answer_invoice(**invoice)
        pending = state_data.get("pending_action")
        if isinstance(pending, dict):
            await state.update_data(pending_action={**pending, "status": "invoice_sent"})
        await message.answer("Счёт отправлен. Оплатите его в Telegram и мы зачислим Stars автоматически.")
        return
    init_data = parsed.get("init_data") or parsed.get("initData") or raw
    if not init_data:
        await message.answer("Получены пустые данные от WebApp.")
        return

    try:
        result = await backend.tg_exchange(init_data)
    except BackendValidationError as exc:
        detail = _first_validation_error(exc.errors)
        await message.answer(
            "Авторизация не удалась: " + detail
        )
        return
    except BackendError as exc:
        await message.answer(
            "Не удалось связаться с сервером для авторизации." + f"\n{exc}"
        )
        return

    await state.update_data(
        access_token=result.get("access"),
        refresh_token=result.get("refresh"),
        profile_payload=result,
    )
    profile = result.get("profile", {})
    summary = _format_summary(
        {
            "city": profile.get("city"),
            "budget": _extract_budget(profile.get("budget")),
            "allergies": profile.get("allergies", []),
            "goals": profile.get("goals"),
        }
    )
    await message.answer(
        "Авторизация прошла успешно! Используйте команду /profile для обновления анкеты.\n"
        + summary
    )
