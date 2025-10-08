from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Tuple


_DEF_BACKEND = "http://backend:8000"


def _clean_backend_url(raw: str | None) -> str:
    value = (raw or "").strip().rstrip("/")
    if value.endswith("/api"):
        value = value[:-4]
    return value or _DEF_BACKEND


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
    admin_ids: Tuple[int, ...]

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
        bot_key = os.getenv("BOT_KEY") or os.getenv("BOT_INTERNAL_KEY") or "super-secret-bot-key"
        backend_base_url = _clean_backend_url(
            os.getenv("BACKEND_BASE_URL") or os.getenv("BACKEND_URL") or os.getenv("API_BASE")
        )
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:5173/")
        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS") or os.getenv("BOT_ADMIN_IDS"))
        return cls(
            token=token,
            bot_key=bot_key,
            backend_base_url=backend_base_url,
            webapp_url=webapp_url,
            admin_ids=admin_ids,
        )


__all__ = ["Config"]
