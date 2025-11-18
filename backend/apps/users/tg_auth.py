from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, Tuple

import httpx

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.logging import summarize_token, telegram_token_fingerprint
from nutribot.middleware import get_request_id

from .api_payloads import build_profile_response
from .models import Profile
from .tg_utils import InitDataVerificationError, verify_init_data

User = get_user_model()

try:  # pragma: no cover - depends on project configuration
    User._meta.get_field("telegram_id")
    USER_HAS_TELEGRAM_FIELD = True
except FieldDoesNotExist:  # pragma: no cover - default local setup
    USER_HAS_TELEGRAM_FIELD = False

logger = logging.getLogger("audit.auth")
tg_logger = logging.getLogger("audit.telegram")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def should_send_webapp_confirmation(request) -> bool:
    query_params = getattr(request, "query_params", {}) or {}
    body = getattr(request, "data", {}) or {}
    return _coerce_bool(
        query_params.get("confirm")
        or body.get("send_webapp_confirmation")
        or body.get("confirm")
    )


def _ensure_profile_telegram_id(user, tg_id: int) -> Tuple[Profile, bool]:
    profile, created = Profile.objects.get_or_create(user=user)
    if profile.telegram_id != tg_id:
        profile.telegram_id = tg_id
        profile.save(update_fields=["telegram_id"])
    return profile, created


@transaction.atomic
def _get_user_by_telegram_id(tg_id: int, username: str) -> Tuple[Any, bool, bool]:
    """Return user bound to the Telegram id, creating a link if needed."""

    if USER_HAS_TELEGRAM_FIELD:
        user, created = User.objects.get_or_create(
            telegram_id=tg_id, defaults={"username": username}
        )
        if getattr(user, "telegram_id", None) != tg_id:
            user.telegram_id = tg_id
            user.save(update_fields=["telegram_id"])
        profile, profile_created = _ensure_profile_telegram_id(user, tg_id)
        return user, created, profile_created

    profile = (
        Profile.objects.select_related("user").filter(telegram_id=tg_id).first()
    )
    if profile:
        return profile.user, False, False

    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    profile, profile_created = _ensure_profile_telegram_id(user, tg_id)
    return user, created, profile_created


class TelegramWebAppAuthError(Exception):
    """Raised when Telegram WebApp initData validation fails."""

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        details: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason or message
        self.details = details or {}


def exchange_webapp_init_data(
    init_data: str | None,
    *,
    bot_token: str | None = None,
) -> Dict[str, Any]:
    if not init_data:
        raise TelegramWebAppAuthError("initData is required", reason="missing_init_data")

    token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    rid = get_request_id()
    base_extra: Dict[str, Any] = {
        "rid": rid,
        "request_id": rid,
        "token_fingerprint": telegram_token_fingerprint(token),
        "token_source": getattr(settings, "TELEGRAM_BOT_TOKEN_SOURCE", "unknown"),
    }

    try:
        parsed = verify_init_data(init_data, token)
    except InitDataVerificationError as exc:
        tg_logger.warning(
            "exchange init_data invalid",
            extra={**base_extra, "reason": exc.reason, "details": exc.details},
        )
        raise TelegramWebAppAuthError(
            f"invalid initData: {exc.reason}",
            reason=exc.reason,
            details=exc.details,
        ) from exc
    except Exception as exc:  # pragma: no cover - depends on Telegram payload
        tg_logger.exception(
            "exchange init_data unexpected_error",
            extra={**base_extra, "error": str(exc)},
        )
        raise TelegramWebAppAuthError("invalid initData: unexpected_error") from exc

    meta = parsed.pop("__meta__", {}) if isinstance(parsed, dict) else {}

    tg_logger.info(
        "exchange init_data verified",
        extra={
            **base_extra,
            "claims": sorted(parsed.keys()),
            "meta": meta,
            "query_id": parsed.get("query_id"),
        },
    )

    user_json = parsed.get("user")
    if not user_json or not isinstance(user_json, dict):
        raise TelegramWebAppAuthError("user missing in initData", reason="user_missing")

    tg_id = user_json.get("id")
    if not tg_id:
        raise TelegramWebAppAuthError("telegram id missing", reason="telegram_id_missing")

    username = str(user_json.get("username") or f"tg_{tg_id}")
    user, user_created, profile_created = _get_user_by_telegram_id(int(tg_id), username)
    if user_created:
        user.first_name = user_json.get("first_name") or ""
        user.last_name = user_json.get("last_name") or ""
        user.save(update_fields=["first_name", "last_name"])

    profile = Profile.objects.select_related("user").get(user=user)
    payload = build_profile_response(user, profile)
    payload.update(
        {
            "telegram_user_id": profile.telegram_id,
            "web_app_query_id": parsed.get("query_id"),
        }
    )

    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    exp_raw = access_token.get("exp")
    try:
        exp = int(exp_raw) if exp_raw is not None else None
    except Exception:
        try:
            exp = int(datetime.fromtimestamp(exp_raw).timestamp()) if exp_raw else None
        except Exception:
            exp = None

    payload.update(
        {
            "access": str(access_token),
            "refresh": str(refresh),
            "exp": exp,
        }
    )

    from .models import TelegramSession

    expires_at = (
        datetime.fromtimestamp(exp, tz=dt_timezone.utc) if isinstance(exp, int) else None
    )
    TelegramSession.objects.update_or_create(
        profile=profile,
        defaults={
            "access_token": str(access_token),
            "refresh_token": str(refresh),
            "expires_at": expires_at,
        },
    )

    tg_logger.info(
        "exchange init_data resolved",
        extra={
            **base_extra,
            "telegram_user_id": profile.telegram_id,
            "user_id": getattr(user, "id", None),
            "user_created": user_created,
            "profile_created": profile_created,
        },
    )
    logger.info(
        "webapp exchange tokens",
        extra={
            **base_extra,
            "telegram_user_id": profile.telegram_id,
            "user_id": getattr(user, "id", None),
            "access": summarize_token(str(access_token)),
            "refresh": summarize_token(str(refresh)),
            "exp": int(exp) if isinstance(exp, int) else exp,
        },
    )
    return payload


def send_webapp_auth_confirmation(
    query_id: str | None, *, rid: str, telegram_user_id: int | None = None
) -> None:
    if not query_id:
        return

    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    extra = {
        "rid": rid,
        "query_id": query_id,
        "telegram_user_id": telegram_user_id,
        "token_source": getattr(settings, "TELEGRAM_BOT_TOKEN_SOURCE", "unknown"),
        "token_fingerprint": telegram_token_fingerprint(token),
    }

    if not token:
        logger.warning("webapp auth confirmation skipped", extra={**extra, "reason": "missing_token"})
        return

    result = {
        "type": "article",
        "id": query_id,
        "title": "Авторизация",
        "input_message_content": {"message_text": "Авторизация завершена ✅"},
    }

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/answerWebAppQuery",
            json={"web_app_query_id": query_id, "result": result},
            timeout=6.0,
        )
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        ok = response.status_code == 200 and isinstance(data, dict) and data.get("ok") is True
        logger.info(
            "webapp auth confirmation sent",
            extra={**extra, "status": response.status_code, "ok": ok},
        )
        if not ok:
            logger.warning(
                "webapp auth confirmation rejected",
                extra={**extra, "status": response.status_code, "response": data},
            )
    except Exception as exc:  # pragma: no cover - network/runtime
        logger.warning(
            "webapp auth confirmation failed",
            extra={**extra, "error": str(exc)},
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def tg_exchange(request):
    """
    Body: { "init_data": "<raw initData from Telegram WebApp>" }
    """

    init_data = request.data.get("init_data")
    try:
        payload = exchange_webapp_init_data(init_data)
    except TelegramWebAppAuthError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    rid = getattr(request, "request_id", get_request_id())
    query_id = payload.pop("web_app_query_id", None)
    if should_send_webapp_confirmation(request) and query_id:
        send_webapp_auth_confirmation(
            query_id, rid=rid, telegram_user_id=payload.get("telegram_user_id")
        )
    return Response(payload)
