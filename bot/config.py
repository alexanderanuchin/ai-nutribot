from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Tuple

_DEF_BACKEND = "http://backend:8000"
_DEF_WEBAPP = "http://localhost:5173/"

_API_URL_KEYS = (
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
    for key in _API_URL_KEYS:
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


def _read_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _optional_url(raw: str | None) -> str | None:
    value = (raw or "").strip()
    return value or None


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
    redis_host: str
    redis_port: int
    privacy_url: str | None
    terms_url: str | None
    support_url: str | None
    experimental_menu: bool

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
        bot_key = os.getenv("BOT_KEY") or os.getenv("BOT_INTERNAL_KEY") or "super-secret-bot-key"
        backend_base_url = resolve_backend_url()
        webapp_url = os.getenv("WEBAPP_URL") or _DEF_WEBAPP
        bot_username = os.getenv("BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME") or ""
        throttle_limit = int(os.getenv("BOT_THROTTLE_LIMIT", "3"))
        throttle_interval = float(os.getenv("BOT_THROTTLE_INTERVAL", "10"))
        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS") or os.getenv("BOT_ADMIN_IDS"))
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        privacy_url = _optional_url(os.getenv("PRIVACY_URL"))
        terms_url = _optional_url(os.getenv("TERMS_URL"))
        support_url = _optional_url(os.getenv("SUPPORT_URL"))
        experimental_menu = _read_bool(os.getenv("BOT_EXPERIMENTAL_MENU"))
        return cls(
            token=token,
            bot_key=bot_key,
            backend_base_url=backend_base_url,
            webapp_url=webapp_url,
            bot_username=bot_username,
            throttle_limit=throttle_limit,
            throttle_interval=throttle_interval,
            admin_ids=admin_ids,
            redis_host=redis_host,
            redis_port=redis_port,
            privacy_url=privacy_url,
            terms_url=terms_url,
            support_url=support_url,
            experimental_menu=experimental_menu,
        )

    @property
    def webapp_webview_url(self) -> str | None:
        url = (self.webapp_url or "").strip()
        return url if url.lower().startswith("https://") else None

    @property
    def webapp_browser_url(self) -> str | None:
        url = (self.webapp_url or "").strip()
        if url.lower().startswith("https://"):
            return url
        return None


__all__ = [
    "Config",
    "_DEF_BACKEND",
    "_API_URL_KEYS",
    "_clean_backend_url",
    "resolve_backend_url",
]
