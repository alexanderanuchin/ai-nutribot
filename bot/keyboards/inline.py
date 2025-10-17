from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


class QuickAction(str, Enum):
    WALLET_TOP_UP = "wallet_top_up"
    CHANGE_PLAN = "change_plan"


class QuickActionCallback(CallbackData, prefix="quick"):
    action: QuickAction


@dataclass(slots=True)
class CRMEntryPoint:
    url: str | None
    deep_link: str | None


def build_quick_actions_keyboard(
    *,
    crm_entry: CRMEntryPoint,
    include_wallet: bool = True,
    include_change_plan: bool = True,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if include_wallet:
        builder.button(
            text="💳 Пополнить кошелёк",
            callback_data=QuickActionCallback(action=QuickAction.WALLET_TOP_UP).pack(),
        )
    if crm_entry.url:
        builder.button(text="🗂️ Открыть CRM", web_app=WebAppInfo(url=crm_entry.url))
    elif crm_entry.deep_link:
        builder.button(text="🗂️ Открыть CRM", url=crm_entry.deep_link)
    if include_change_plan:
        builder.button(
            text="🧾 Сменить тариф",
            callback_data=QuickActionCallback(action=QuickAction.CHANGE_PLAN).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()


def create_crm_entry_point(*, webapp_url: str | None, bot_username: str | None) -> CRMEntryPoint:
    raw_url = (webapp_url or "").strip()
    url = raw_url if raw_url.lower().startswith("https://") else None
    deep_link = None
    if not url and bot_username:
        username = bot_username.lstrip("@")
        deep_link = f"https://t.me/{username}/app?startapp=dashboard"
    return CRMEntryPoint(url=url, deep_link=deep_link)


__all__ = [
    "CRMEntryPoint",
    "QuickAction",
    "QuickActionCallback",
    "build_quick_actions_keyboard",
    "create_crm_entry_point",
]