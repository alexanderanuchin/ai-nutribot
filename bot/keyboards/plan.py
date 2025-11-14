from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.constants import TOPUP_AMOUNTS


def period_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="7 дней", callback_data="plan:period:7")
    builder.button(text="14 дней", callback_data="plan:period:14")
    builder.button(text="Отмена", callback_data="plan:cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def generate_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Сгенерировать", callback_data="plan:generate")
    builder.button(text="Отмена", callback_data="plan:cancel")
    builder.adjust(1, 1)
    return builder.as_markup()


def summary_actions_keyboard(plan_id: int, daily_kcal: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"plan:accept:{plan_id}")
    builder.button(text="🚫 Отклонить", callback_data=f"plan:reject:{plan_id}")
    builder.button(text="♻️ Пересчитать", callback_data=f"plan:regen:{plan_id}:{daily_kcal}")
    builder.adjust(2, 1)
    return builder.as_markup()


def regeneration_options_keyboard(plan_id: int, daily_kcal: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="-10% калорий", callback_data=f"plan:regen_adjust:{plan_id}:less:{daily_kcal}")
    builder.button(text="+10% калорий", callback_data=f"plan:regen_adjust:{plan_id}:more:{daily_kcal}")
    builder.button(text="Без изменений", callback_data=f"plan:regen_adjust:{plan_id}:same:{daily_kcal}")
    builder.button(text="Отмена", callback_data="plan:regen_cancel")
    builder.adjust(2, 2)
    return builder.as_markup()


def plan_topup_keyboard(
        *,
        amounts: Iterable[int] | None = None,
        webapp_url: str | None = None,
        support_url: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    values = tuple(amounts) if amounts is not None else TOPUP_AMOUNTS
    for value in values:
        builder.button(text=f"Пополнить {value} XTR", callback_data=f"plan:topup:{value}")
    if webapp_url:
        if webapp_url.lower().startswith("https://"):
            builder.button(text="Другая сумма", web_app=WebAppInfo(url=webapp_url))
        else:
            builder.button(text="Другая сумма", url=webapp_url)
    elif support_url:
        builder.button(text="Поддержка", url=support_url)
    builder.adjust(1)
    return builder.as_markup()
