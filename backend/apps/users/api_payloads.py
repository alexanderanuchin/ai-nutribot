"""Helpers for constructing consistent API payloads for profile endpoints."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict

from django.contrib.auth import get_user_model

from .models import Profile
from .serializers import ProfileSerializer, UserSerializer
from .services import get_profile_stars_balance

User = get_user_model()


def _ensure_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _format_decimal(value: Decimal, quant: Decimal) -> str:
    normalized = value.quantize(quant, rounding=ROUND_HALF_UP)
    return format(normalized, "f")


def build_wallet_payload(profile: Profile) -> Dict[str, str]:
    stars_value = Decimal(get_profile_stars_balance(profile))
    calo_value = _ensure_decimal(getattr(profile, "calocoin_balance", 0))

    try:
        from apps.orders.models import WalletTransaction
        from apps.orders.services.wallet import get_wallet_balance
    except Exception:  # pragma: no cover - orders app may not be installed in tests
        pass
    else:
        try:
            stars_balance = get_wallet_balance(
                profile, WalletTransaction.Currency.TELEGRAM_STARS
            )
            stars_value = stars_balance.available
        except Exception:  # pragma: no cover - fall back to cached balances
            pass
        try:
            calo_balance = get_wallet_balance(
                profile, WalletTransaction.Currency.CALOCOIN
            )
            calo_value = calo_balance.available
        except Exception:  # pragma: no cover - fall back to cached balances
            pass

    return {
        "stars": _format_decimal(_ensure_decimal(stars_value), Decimal("1")),
        "calo": _format_decimal(_ensure_decimal(calo_value), Decimal("0.01")),
    }


def build_profile_response(user: User, profile: Profile) -> Dict[str, Any]:
    profile_data = ProfileSerializer(profile, include_user=False).data
    user_data = UserSerializer(user).data
    user_data.setdefault("phone", user.get_username())

    wallet = build_wallet_payload(profile)
    metrics = profile_data.get("metrics")

    return {
        "user": user_data,
        "profile": profile_data,
        "wallet": wallet,
        "metrics": metrics,
    }