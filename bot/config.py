from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Tuple


_DEF_BACKEND = "http://backend:8000"


_DEF_API_KEYS = (
    "BACKEND_API_URL",
    "BACKEND_BASE_URL",
    "API_BASE",
    "BACKEND_URL",
)


def _clean_backend_url(raw: str | None) -> str:
    value = (raw or "").strip().rstrip("/")
    if value.endswith("/api"):
        value = value[:-4]
    return value or _DEF_BACKEND


def resolve_backend_url() -> str:
    for key in _DEF_API_KEYS:
        candidate = os.getenv(key)
        value = _clean_backend_url(candidate)
        if value != _DEF_BACKEND or candidate:
            return value
    return _DEF_BACKEND


def _parse_admin_ids(raw: str | None) -> Tuple[int, ...]:
    if not raw:
        return ()
    parts: Iterable[str] = raw.replace(";", ",").split(",")
    result = []
    for chunk in parts:
        candidate = chunk.strip()
        if not candidate:
            continue
        try:
            result.append(int(candidate))
        except ValueError:
            continue
    return tuple(dict.fromkeys(result))


@dataclass(slots=True)
class Config:
    token: str
    bot_key: str
    backend_base_url: str
    webapp_url: str
    bot_username: str
    throttle_limit: int
    throttle_interval: float
    admin_ids: Tuple[int, ...]

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
        bot_key = os.getenv("BOT_KEY") or os.getenv("BOT_INTERNAL_KEY") or "super-secret-bot-key"
        backend_base_url = resolve_backend_url()
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:5173/")
        bot_username = os.getenv("BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME") or ""
        throttle_limit = int(os.getenv("BOT_THROTTLE_LIMIT", "3"))
        throttle_interval = float(os.getenv("BOT_THROTTLE_INTERVAL", "10"))
        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS") or os.getenv("BOT_ADMIN_IDS"))
        return cls(
            token=token,
            bot_key=bot_key,
            backend_base_url=backend_base_url,
            webapp_url=webapp_url,
            bot_username=bot_username,
            throttle_limit=throttle_limit,
            throttle_interval=throttle_interval,
            admin_ids=admin_ids,
        )


__all__ = ["Config", "resolve_backend_url", "_DEF_BACKEND", "_DEF_API_KEYS", "_clean_backend_url"]
