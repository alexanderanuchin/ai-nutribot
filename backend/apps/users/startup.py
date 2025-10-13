from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Any, Dict

import httpx
from django.conf import settings

from apps.common.logging import telegram_token_fingerprint
from nutribot.middleware import get_build_fingerprint, get_request_id


logger = logging.getLogger("audit.telegram")
_startup_lock = Lock()
_startup_logged = False


def _build_startup_extra() -> Dict[str, Any]:
    rid = get_request_id("-")
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    token_source = getattr(settings, "TELEGRAM_BOT_TOKEN_SOURCE", "unknown")
    return {
        "rid": rid,
        "request_id": rid,
        "token_fingerprint": telegram_token_fingerprint(token),
        "token_source": token_source,
        "settings_module": os.getenv("DJANGO_SETTINGS_MODULE", ""),
        "build_fingerprint": get_build_fingerprint(),
    }


def log_bot_startup_metadata() -> None:
    """Log diagnostic information about the configured Telegram bot."""

    global _startup_logged
    with _startup_lock:
        if _startup_logged:
            return
        _startup_logged = True

    extra = _build_startup_extra()
    logger.info("telegram bot startup", extra=extra)

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("telegram bot token missing", extra=extra)
        return

    try:
        with httpx.Client(timeout=httpx.Timeout(5.0, connect=5.0)) as client:
            response = client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = response.json()
    except Exception as exc:  # pragma: no cover - network interaction
        logger.warning(
            "telegram bot getMe failed",
            extra={**extra, "error": str(exc)},
        )
        return

    if not isinstance(data, dict):
        logger.warning(
            "telegram bot getMe invalid",
            extra={**extra, "status_code": response.status_code, "body_type": type(data).__name__},
        )
        return

    if not data.get("ok"):
        logger.warning(
            "telegram bot getMe rejected",
            extra={
                **extra,
                "status_code": response.status_code,
                "description": data.get("description"),
            },
        )
        return

    result = data.get("result") or {}
    logger.info(
        "telegram bot identity",
        extra={
            **extra,
            "bot_username": result.get("username"),
            "bot_id": result.get("id"),
            "first_name": result.get("first_name"),
            "can_join_groups": result.get("can_join_groups"),
        },
    )


__all__ = ["log_bot_startup_metadata"]