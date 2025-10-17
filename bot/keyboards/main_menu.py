from __future__ import annotations

from typing import Iterable, Sequence

from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

MAIN_MENU_BUTTONS: Sequence[str] = (
    "🏠 Главная",
    "👤 Профиль",
    "🧾 Тариф",
    "📜 История",
    "👛 Кошелёк",
    "🆘 Поддержка",
    "💳 Оплата/помощь",
    "📄 Условия",
    "✖️ Отмена",
)


def _normalize_layout(layout: Iterable[int] | None, total: int) -> list[int]:
    rows: list[int] = []
    remaining = total
    if layout:
        for chunk in layout:
            if chunk <= 0:
                continue
            rows.append(min(chunk, remaining))
            remaining -= rows[-1]
            if remaining <= 0:
                break
    if remaining > 0:
        # По умолчанию формируем компактные ряды по 3 кнопки.
        while remaining > 3:
            rows.append(3)
            remaining -= 3
        rows.append(remaining)
    return rows


def build_main_menu_keyboard(*, layout: Iterable[int] | None = (3, 3, 3)) -> ReplyKeyboardMarkup:
    """Собирает клавиатуру главного меню с учётом ширины экранов."""

    builder = ReplyKeyboardBuilder()
    for caption in MAIN_MENU_BUTTONS:
        builder.button(text=caption)

    builder.adjust(*_normalize_layout(layout, len(MAIN_MENU_BUTTONS)))
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
        selective=False,
        one_time_keyboard=False,
    )


__all__ = ["build_main_menu_keyboard", "MAIN_MENU_BUTTONS"]