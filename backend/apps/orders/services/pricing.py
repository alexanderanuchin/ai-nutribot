from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

from django.conf import settings

from apps.users.models import Profile


@dataclass(slots=True)
class Pricing:
    action: str
    amount: int
    currency: str
    title: str | None = None
    description: str | None = None
    metadata: Dict[str, Any] | None = None

    def as_payload(self) -> Dict[str, Any]:
        meta = dict(self.metadata or {})
        return {
            "action": self.action,
            "amount": int(self.amount),
            "currency": self.currency.upper(),
            "title": self.title,
            "description": self.description,
            "metadata": meta,
        }


class PricingNotConfigured(RuntimeError):
    """Raised when pricing for a wallet action is missing."""

    def __init__(self, action: str):
        super().__init__(f"Pricing for action '{action}' is not configured")
        self.action = action


def _resolve_config_source(action: str) -> Mapping[str, Any] | Callable[..., Mapping[str, Any]]:
    config = getattr(settings, "WALLET_ACTION_PRICING", {}) or {}
    raw = config.get(action)
    if raw is None:
        raise PricingNotConfigured(action)
    return raw


def _coerce_pricing(action: str, payload: Mapping[str, Any]) -> Pricing:
    amount = payload.get("amount")
    if amount is None:
        raise PricingNotConfigured(action)
    try:
        normalized_amount = int(amount)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise PricingNotConfigured(action) from exc
    if normalized_amount <= 0:
        raise PricingNotConfigured(action)
    currency = str(payload.get("currency") or "STARS").upper()
    title = payload.get("title")
    description = payload.get("description")
    metadata_raw = payload.get("metadata")
    metadata: Dict[str, Any] | None = None
    if isinstance(metadata_raw, Mapping):
        metadata = dict(metadata_raw)
    return Pricing(
        action=action,
        amount=normalized_amount,
        currency=currency,
        title=str(title) if isinstance(title, str) and title else None,
        description=str(description) if isinstance(description, str) and description else None,
        metadata=metadata,
    )


def get_wallet_action_pricing(
        action: str,
        *,
        profile: Profile | None = None,
        context: Mapping[str, Any] | None = None,
) -> Pricing:
    """Resolve pricing metadata for the requested wallet-backed action."""

    source = _resolve_config_source(action)
    if callable(source):
        resolved = source(profile=profile, context=context)
        if not isinstance(resolved, Mapping):
            raise PricingNotConfigured(action)
        payload: Mapping[str, Any] = resolved
    else:
        payload = source
    return _coerce_pricing(action, payload)


__all__ = [
    "Pricing",
    "PricingNotConfigured",
    "get_wallet_action_pricing",
]
