from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx
from django.conf import settings
from django.db import transaction
from django.db.models import Case, F, IntegerField, Sum, Value, When
from django.utils import timezone

from ..models import Profile, TelegramStarLedgerEntry

if TYPE_CHECKING:  # pragma: no cover
    from apps.orders.models import WalletTransaction


@dataclass(frozen=True)
class StarsBalance:
    amount: int
    currency: str = "XTR"
    updated_at: timezone.datetime | None = None


def _direction_from_transaction(direction: str) -> str:
    if direction == "credit":
        return TelegramStarLedgerEntry.Direction.CREDIT
    return TelegramStarLedgerEntry.Direction.DEBIT


def get_profile_stars_balance(profile: Profile) -> int:
    aggregate = profile.star_ledger_entries.aggregate(
        total=Sum(
            Case(
                When(
                    direction=TelegramStarLedgerEntry.Direction.CREDIT,
                    then=F("amount"),
                ),
                When(
                    direction=TelegramStarLedgerEntry.Direction.DEBIT,
                    then=-F("amount"),
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    )
    return int(aggregate.get("total") or 0)


def refresh_profile_stars_cache(profile: Profile) -> int:
    balance = get_profile_stars_balance(profile)
    if profile.telegram_stars_balance != balance:
        profile.telegram_stars_balance = balance
        profile.save(update_fields=["telegram_stars_balance", "updated_at"])
    return balance


def get_user_stars_balance(user) -> int:
    profile, _ = Profile.objects.get_or_create(user=user)
    return get_profile_stars_balance(profile)


def build_stars_balance_payload(profile: Profile) -> Dict[str, Any]:
    balance = get_profile_stars_balance(profile)
    return {
        "balance": {
            "amount": balance,
            "currency": "XTR",
            "updated_at": timezone.now().isoformat(),
        },
        "transactions": [
            {
                "id": entry.pk,
                "direction": "in" if entry.direction == TelegramStarLedgerEntry.Direction.CREDIT else "out",
                "amount": entry.amount,
                "occurred_at": entry.occurred_at.isoformat(),
                "description": entry.description or None,
                "source": entry.source or None,
                "metadata": entry.metadata or {},
            }
            for entry in profile.star_ledger_entries.select_related("wallet_transaction").order_by("-occurred_at")[:50]
        ],
    }


def _extract_charge_id(metadata: Dict[str, Any]) -> Optional[str]:
    value = metadata.get("telegram_payment_charge_id") or metadata.get("charge_id")
    if isinstance(value, str) and value:
        return value
    return None


def sync_stars_ledger_for_transaction(transaction: "WalletTransaction") -> Optional[TelegramStarLedgerEntry]:
    from apps.orders.models import WalletTransaction  # Imported lazily to avoid circular imports

    if transaction.currency != WalletTransaction.Currency.TELEGRAM_STARS:
        return None
    if transaction.direction not in (
        WalletTransaction.Direction.CREDIT,
        WalletTransaction.Direction.DEBIT,
    ):
        return None
    if transaction.status != WalletTransaction.Status.CONFIRMED:
        return None

    metadata: Dict[str, Any] = dict(transaction.metadata or {})
    charge_id = _extract_charge_id(metadata)
    defaults = {
        "profile": transaction.profile,
        "direction": _direction_from_transaction(transaction.direction),
        "amount": int(transaction.amount),
        "occurred_at": transaction.occurred_at,
        "description": transaction.description or "",
        "source": metadata.get("source") or (transaction.reference or ""),
        "metadata": metadata,
        "telegram_payment_charge_id": charge_id,
    }
    entry, created = TelegramStarLedgerEntry.objects.get_or_create(
        wallet_transaction=transaction,
        defaults=defaults,
    )
    if not created:
        updates: Dict[str, Any] = {}
        for field, value in defaults.items():
            if getattr(entry, field) != value:
                updates[field] = value
        if updates:
            for key, value in updates.items():
                setattr(entry, key, value)
            entry.save(update_fields=list(updates) + ["updated_at"])
    refresh_profile_stars_cache(transaction.profile)
    return entry


def get_bot_star_balance(*, timeout: float = 5.0) -> StarsBalance:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"https://api.telegram.org/bot{token}/getMyStarBalance"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description") or "Failed to fetch bot star balance")
    result = data.get("result") or {}
    amount = int(result.get("star_count", 0))
    return StarsBalance(amount=amount, updated_at=timezone.now())


@transaction.atomic
def ensure_stars_ledger_for_transaction(transaction: "WalletTransaction") -> Optional[TelegramStarLedgerEntry]:
    entry = sync_stars_ledger_for_transaction(transaction)
    if entry is None:
        return None
    return entry