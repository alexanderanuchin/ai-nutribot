from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict
from urllib.parse import parse_qsl


class InitDataVerificationError(ValueError):
    """Raised when Telegram initData fails validation."""

    def __init__(self, reason: str, *, details: Dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def verify_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """Validate Telegram WebApp init data and return parsed payload."""

    if not init_data:
        raise InitDataVerificationError("init_data missing")
    if not bot_token:
        raise InitDataVerificationError("token missing")

    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
    except ValueError as exc:
        raise InitDataVerificationError("parse error", details={"error": str(exc)}) from exc

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise InitDataVerificationError("hash missing")

    sorted_keys = sorted(params.keys())
    data_check_items = [f"{key}={params[key]}" for key in sorted_keys]
    data_check = "\n".join(data_check_items)
    base_len = len(data_check)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calc_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    if calc_hash != received_hash:
        raise InitDataVerificationError(
            "hash mismatch",
            details={
                "expected_hash": calc_hash[:8],
                "received_hash": received_hash[:8],
                "base_string_len": base_len,
            },
        )

    parsed: Dict[str, Any] = {}
    for key, value in params.items():
        if key in {"user", "receiver", "chat"}:
            try:
                parsed[key] = json.loads(value)
            except Exception:
                parsed[key] = value
        else:
            parsed[key] = value

        parsed["__meta__"] = {
            "base_string_len": base_len,
            "keys": sorted_keys,
        }
    return parsed


__all__ = ["verify_init_data", "InitDataVerificationError"]