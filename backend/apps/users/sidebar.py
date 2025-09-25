from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List

from apps.users.models import Profile


_CALO_BOT_LINK = "https://t.me/CaloIQ_bot"
_CALO_BOT_SCENARIOS = f"{_CALO_BOT_LINK}?start=scenarios"
_CALO_BOT_MARKET = f"{_CALO_BOT_LINK}?start=market"
_CALO_BOT_AUTOPAY = f"{_CALO_BOT_LINK}?start=autopay"
_CALO_BOT_PRO = f"{_CALO_BOT_LINK}?start=calopro"
_TELEGRAM_STAR_TOPUP = "https://t.me/wallet?start=star-topup"


@dataclass
class _FeatureState:
    key: str
    title: str
    description: str
    href: str
    state: str
    status_label: str
    action_label: str
    badge: str | None = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "href": self.href,
            "state": self.state,
            "status_label": self.status_label,
            "action_label": self.action_label,
            "badge": self.badge,
        }


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, "", 0, 0.0):
        return False
    return True


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def build_profile_sidebar_meta(profile: Profile) -> Dict[str, Any]:
    user = profile.user
    has_telegram = _bool(getattr(user, "telegram_id", None) or profile.telegram_id)
    has_city = bool(profile.city)
    has_daily_budget = _bool(profile.daily_budget)
    stars_balance = int(getattr(profile, "telegram_stars_balance", 0) or 0)
    calocoin_balance = _decimal(getattr(profile, "calocoin_balance", 0))
    has_balance = stars_balance > 0 or calocoin_balance > 0

    assistants: List[_FeatureState] = []

    ai_state = "active" if has_telegram else "inactive"
    assistants.append(
        _FeatureState(
            key="ai_consultant",
            title="AI-консультант здоровья",
            description=(
                "Алгоритм синхронизирует меню, воду и уведомления каждые 6 часов,"
                " чтобы поддерживать комфортный ритм."
            ),
            href=_CALO_BOT_SCENARIOS if has_telegram else _CALO_BOT_LINK,
            state=ai_state,
            status_label="Активен" if has_telegram else "Подключите Telegram",
            action_label="Открыть сценарии" if has_telegram else "Подключить",
            badge="активно" if has_telegram else "доступно",
        )
    )

    trainer_connected = profile.experience_level in {
        Profile.ExperienceLevel.PRO,
        Profile.ExperienceLevel.LEGEND,
    }
    assistants.append(
        _FeatureState(
            key="personal_trainer",
            title="Личный тренер и расписание",
            description=(
                "Синхронизация тренировок и заметок — рекомендации учитывают ваш прогресс"
                " и обновляются вместе с экспертом."
            ),
            href=_CALO_BOT_MARKET,
            state="active" if trainer_connected else "inactive",
            status_label="Подключено" if trainer_connected else "Выберите тренера",
            action_label="Перейти" if trainer_connected else "Подобрать",
            badge="подключено" if trainer_connected else "маркетплейс",
        )
    )

    services: List[_FeatureState] = []
    services.append(
        _FeatureState(
            key="smart_delivery",
            title="Умная доставка еды",
            description="Маркетплейс здоровой еды с расписанием под ваши тренировки и город.",
            href=_CALO_BOT_MARKET,
            state="active" if has_city else "onboarding",
            status_label="Доступно" if has_city else "Укажите город",
            action_label="Открыть",
        )
    )
    services.append(
        _FeatureState(
            key="product_kits",
            title="Конструктор продуктовых наборов",
            description="Подберите боксы для офиса, тренировок и путешествий с учётом бюджета.",
            href=_CALO_BOT_LINK,
            state="active" if has_daily_budget else "onboarding",
            status_label="Готов к расчётам" if has_daily_budget else "Добавьте бюджет",
            action_label="Настроить",
        )
    )
    services.append(
        _FeatureState(
            key="stock_management",
            title="Управление запасами",
            description="Следите за суперфудами и добавками, автопополнение включается по балансу.",
            href=_CALO_BOT_AUTOPAY,
            state="active" if has_balance else "onboarding",
            status_label="Синхронизировано" if has_balance else "Пополните баланс",
            action_label="Открыть",
        )
    )

    wallet_links = {
        "bot": _CALO_BOT_LINK,
        "topup": _TELEGRAM_STAR_TOPUP,
        "topup_onboarding": _CALO_BOT_LINK,
        "autopay": _CALO_BOT_AUTOPAY,
        "pro": _CALO_BOT_PRO,
    }

    onboarding_messages: List[str] = []
    if not has_balance:
        onboarding_messages.append(
            "Пополните Stars или CaloCoin — так активируется сопровождение и бонусы."
        )
    if not has_city:
        onboarding_messages.append(
            "Укажите город, чтобы планировать доставку, курьеров и офлайн-встречи."
        )

    wallet_onboarding = {
        "needs_balance": not has_balance,
        "needs_city": not has_city,
        "messages": onboarding_messages,
    }

    show_wallet = bool(profile.wallet_settings.get("show_wallet", False)) if profile.wallet_settings else False

    wallet_payload = {
        "show_wallet": show_wallet,
        "links": wallet_links,
        "onboarding": wallet_onboarding,
    }

    return {
        "wallet": wallet_payload,
        "assistants": [item.to_payload() for item in assistants],
        "services": [item.to_payload() for item in services],
    }


__all__ = ["build_profile_sidebar_meta"]