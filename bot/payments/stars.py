from __future__ import annotations

import logging
import uuid
from typing import Any, Mapping

from aiogram.types import LabeledPrice

from bot.logkit import get_request_id

logger = logging.getLogger("audit.wallet")


def parse_invoice_payload(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not payload:
        return result
    for item in str(payload).split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key] = value
    return result


def _build_invoice_payload(
        user_id: int,
        amount: int,
        *,
        rid: str | None = None,
        extra: Mapping[str, Any] | None = None,
) -> str:
    token = uuid.uuid4().hex
    parts = [f"uid={user_id}", f"amt={amount}", f"token={token}"]
    if rid:
        parts.append(f"rid={rid}")
    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            key_str = str(key).strip()
            if not key_str:
                continue
            value_str = str(value).replace(";", ":")
            parts.append(f"{key_str}={value_str}")
    return ";".join(parts)


def build_stars_topup_invoice(
    user_id: int,
    amount: int,
    *,
    comment: str | None = None,
    rid: str | None = None,
    provider_token: str | None = None,
    payload_extra: Mapping[str, Any] | None = None,
) -> dict:
    description = f"Быстрое пополнение на {amount} XTR."
    if comment:
        comment_text = comment.strip()
        if comment_text:
            short_comment = comment_text[:180]
            description += f"\nКомментарий: {short_comment}"

    rid_to_use = rid or get_request_id()
    payload = _build_invoice_payload(user_id, amount, rid=rid_to_use, extra=payload_extra)
    payload_meta = parse_invoice_payload(payload)
    token_prefix = (payload_meta.get("token") or "")[:8] if payload_meta else ""
    intent = payload_meta.get("intent") if payload_meta else None
    attempt = payload_meta.get("aid") if payload_meta else None
    action = payload_meta.get("action") if payload_meta else None
    logger.info(
        "wallet invoice_created",
        extra={
            "rid": rid_to_use,
            "telegram_user_id": user_id,
            "amount": amount,
            "currency": "XTR",
            "has_comment": bool(comment and comment.strip()),
            "token_prefix": token_prefix,
            "intent": intent,
            "attempt_id": attempt,
            "action": action,
        },
    )
    prices = [LabeledPrice(label=f"Пополнение {amount} XTR", amount=amount)]
    return {
        "title": "Пополнение баланса Stars",
        "description": description,
        "currency": "XTR",
        "prices": prices,
        "payload": payload,
        "provider_token": provider_token or "",
    }


def plan_topup_payload(state_data: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(state_data, Mapping):
        return {}
    pending = state_data.get("pending_action")
    if not isinstance(pending, Mapping):
        return {}
    if pending.get("type") != "generate_plan":
        return {}
    attempt_id = pending.get("attempt_id")
    try:
        attempt_int = int(attempt_id)
    except (TypeError, ValueError):
        return {}
    return {
        "intent": "plan_topup",
        "aid": str(attempt_int),
        "action": "generate_plan",
    }


__all__ = [
    "build_stars_topup_invoice",
    "parse_invoice_payload",
    "plan_topup_payload",
]
