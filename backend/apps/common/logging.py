from __future__ import annotations

import hashlib
from typing import Any

MASK_PREFIX_LEN = 4


def summarize_token(value: str | None, *, prefix_len: int = MASK_PREFIX_LEN) -> str:
    """Return a safe textual representation of a token for logging."""

    if not value:
        return "present=false"
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:8]
    prefix = value[:prefix_len]
    length = len(value)
    return f"present=true prefix={prefix}*** len={length} sha256={digest}"


def summarize_header(value: str | None) -> str:
    if not value:
        return "present=false"
    return summarize_token(value)


def redact_payload(payload: Any, *, max_length: int = 256) -> Any:
    """Ensure arbitrary payloads are safe for logging."""

    if payload is None:
        return None
    if isinstance(payload, (int, float, bool)):
        return payload
    if isinstance(payload, (list, tuple)):
        return [redact_payload(item, max_length=max_length) for item in list(payload)[:10]]
    if isinstance(payload, dict):
        safe: dict[str, Any] = {}
        for key, value in list(payload.items())[:20]:
            safe[str(key)] = redact_payload(value, max_length=max_length)
        return safe
    text = str(payload)
    if len(text) > max_length:
        return text[:max_length] + "…"
    return text


__all__ = ["summarize_token", "summarize_header", "redact_payload"]