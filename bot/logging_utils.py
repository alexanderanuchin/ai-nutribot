from __future__ import annotations

import hashlib
import json
import logging
import os
from contextvars import ContextVar, Token
from typing import Any

_REQUEST_ID_VAR: ContextVar[str | None] = ContextVar("bot_request_id", default=None)


def generate_request_id() -> str:
    return os.urandom(16).hex()


def set_request_id(value: str) -> Token[str | None]:
    return _REQUEST_ID_VAR.set(value)


def reset_request_id(token: Token[str | None] | None) -> None:
    if token is not None:
        _REQUEST_ID_VAR.reset(token)


def get_request_id(default: str = "-") -> str:
    rid = _REQUEST_ID_VAR.get()
    return rid or default


def mask_token(token: str | None, *, prefix_len: int = 4) -> str:
    if not token:
        return "present=false"
    digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()[:8]
    prefix = token[:prefix_len]
    return f"present=true prefix={prefix}*** len={len(token)} sha256={digest}"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - logging
        record.request_id = get_request_id()
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - logging
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "rid": getattr(record, "request_id", get_request_id()),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


__all__ = [
    "generate_request_id",
    "get_request_id",
    "set_request_id",
    "reset_request_id",
    "mask_token",
    "RequestIdFilter",
    "JsonLogFormatter",
]