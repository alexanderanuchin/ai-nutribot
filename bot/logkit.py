from __future__ import annotations

import hashlib
import logging
import os
import sys
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping


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
        rid = getattr(record, "rid", None) or get_request_id()
        record.rid = rid
        if not getattr(record, "request_id", None):
            record.request_id = rid
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - logging
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "rid": getattr(record, "rid", get_request_id()),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("update_id", "from_user", "chat_id", "event_type", "error"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        extra = getattr(record, "extra", None)
        if isinstance(extra, Mapping):
            payload.update(extra)
        return json_dumps(payload)


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def configure_logging(*, level: str | None = None) -> None:
    level_name = (level or os.getenv("BOT_LOG_LEVEL", "INFO")).upper()
    resolved_level = getattr(logging, level_name, logging.INFO)
    as_json = os.getenv("BOT_LOG_JSON", "0") == "1"

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(resolved_level)
    handler.addFilter(RequestIdFilter())
    if as_json:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] rid=%(rid)s %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)
    logging.getLogger("aiogram.event").setLevel(resolved_level)


@dataclass(slots=True)
class TelemetryLogger:
    name: str

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.name)

    def _prepare_extra(
        self,
        *,
        request: Any | None = None,
        extra: MutableMapping[str, Any] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if extra:
            payload.update(extra)
        payload.update(fields)
        rid = payload.get("rid")
        if request is not None:
            rid = rid or getattr(request, "request_id", None)
        payload["rid"] = rid or get_request_id()
        return payload

    def event(
        self,
        message: str,
        *,
        level: int = logging.INFO,
        request: Any | None = None,
        extra: MutableMapping[str, Any] | None = None,
        **fields: Any,
    ) -> None:
        payload = self._prepare_extra(request=request, extra=extra, **fields)
        self._logger.log(level, message, extra=payload)

    def info(self, message: str, **fields: Any) -> None:
        self.event(message, level=logging.INFO, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.event(message, level=logging.WARNING, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.event(message, level=logging.ERROR, **fields)

    def exception(
        self,
        message: str,
        *,
        request: Any | None = None,
        extra: MutableMapping[str, Any] | None = None,
        **fields: Any,
    ) -> None:
        payload = self._prepare_extra(request=request, extra=extra, **fields)
        self._logger.exception(message, extra=payload)


__all__ = [
    "TelemetryLogger",
    "configure_logging",
    "generate_request_id",
    "get_request_id",
    "JsonLogFormatter",
    "json_dumps",
    "mask_token",
    "RequestIdFilter",
    "reset_request_id",
    "set_request_id",
]
