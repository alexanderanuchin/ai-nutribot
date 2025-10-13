import json
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import parse_qsl

from apps.users.tg_auth import (
    TelegramWebAppAuthError,
    exchange_webapp_init_data,
)
from apps.users.models import Profile
from apps.common.logging import summarize_token, telegram_token_fingerprint
from apps.auth.metrics import increment_login_failure
from nutribot.middleware import get_build_fingerprint, get_request_id

logger = logging.getLogger("audit.auth")

TIME_SKEW_THRESHOLD_SECONDS = 45


def _resolve_init_data_source(request) -> Tuple[str | None, str]:
    header_value = request.headers.get("X-Telegram-Init-Data")
    if header_value:
        return header_value, "header"
    body_value = request.data.get("init_data") if hasattr(request, "data") else None
    if body_value:
        return body_value, "body"
    return None, "missing"


def _inspect_init_data(init_data: str | None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metrics: Dict[str, Any] = {}
    errors: Dict[str, Any] = {}
    if not init_data:
        return metrics, errors

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
    except ValueError as exc:
        errors["parse_error"] = str(exc)
        return metrics, errors

    params = dict(pairs)
    metrics["param_count"] = len(params)
    filtered_keys = [key for key in params.keys() if key != "hash"]
    base_string = "\n".join(f"{key}={params[key]}" for key in sorted(filtered_keys))
    metrics["base_string_len"] = len(base_string)
    metrics["has_hash"] = "hash" in params

    hash_value = params.get("hash")
    if hash_value:
        metrics["hash_prefix"] = hash_value[:8]
        metrics["hash_length"] = len(hash_value)

    auth_date_raw = params.get("auth_date")
    if auth_date_raw:
        try:
            metrics["auth_date"] = int(auth_date_raw)
        except (TypeError, ValueError) as exc:
            errors["auth_date_error"] = str(exc)

    user_raw = params.get("user")
    if user_raw:
        try:
            user_payload = json.loads(user_raw)
            if isinstance(user_payload, dict):
                metrics["user_id"] = user_payload.get("id")
                if user_payload.get("username"):
                    metrics["username"] = user_payload.get("username")
            else:
                errors["user_error"] = "invalid_user_payload"
        except json.JSONDecodeError as exc:
            errors["user_error"] = str(exc)

    return metrics, errors


def _compute_time_skew(auth_date: int | None) -> Tuple[float | None, bool]:
    if auth_date is None:
        return None, False
    try:
        auth_dt = datetime.fromtimestamp(auth_date, tz=dt_timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None, False
    server_now = timezone.now()
    skew_seconds = (server_now - auth_dt).total_seconds()
    return skew_seconds, abs(skew_seconds) > TIME_SKEW_THRESHOLD_SECONDS


def _resolve_failure_reason(
        reason_code: str | None,
        parse_errors: Dict[str, Any],
        skew_flag: bool,
        source: str,
) -> str:
    if reason_code in {"missing_init_data", "initData is required"}:
        return "missing_header"
    if reason_code == "hash mismatch":
        return "hash_mismatch"
    if reason_code == "parse error" or parse_errors:
        return "parse_error"
    if reason_code == "token missing":
        return "token_missing"
    if skew_flag:
        return "time_skew"
    if source == "body" and not reason_code:
        return "header_missing_body_used"
    return reason_code or "unknown"


class WebAppLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        init_data, init_source = _resolve_init_data_source(request)
        rid = getattr(request, "request_id", get_request_id())
        token_value = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        token_source = getattr(settings, "TELEGRAM_BOT_TOKEN_SOURCE", "unknown")
        metrics, parse_errors = _inspect_init_data(init_data)
        auth_date = metrics.get("auth_date") if isinstance(metrics, dict) else None
        skew_seconds, skew_flag = _compute_time_skew(auth_date if isinstance(auth_date, int) else None)
        server_now = timezone.now()

        log_extra: Dict[str, Any] = {
            "rid": rid,
            "request_id": rid,
            "build_fingerprint": get_build_fingerprint(),
            "init_data_present": bool(init_data),
            "init_data_length": len(init_data) if init_data else 0,
            "init_data_source": init_source,
            "init_data": summarize_token(init_data),
            "token_fingerprint": telegram_token_fingerprint(token_value),
            "token_source": token_source,
            "server_time": server_now.isoformat(),
        }

        if isinstance(metrics, dict):
            for key in ("user_id", "auth_date", "base_string_len", "hash_length", "hash_prefix", "param_count"):
                if metrics.get(key) is not None:
                    log_extra[key] = metrics[key]
        if skew_seconds is not None:
            log_extra["time_skew_seconds"] = round(skew_seconds, 2)
            log_extra["time_skew_flag"] = skew_flag
        if parse_errors:
            log_extra["parse_errors"] = parse_errors

        logger.info("webapp login request", extra=log_extra)
        if not init_data:
            increment_login_failure("missing_header")
            logger.warning(
                "webapp login failed",
                extra={**log_extra, "reason": "missing_header"},
            )
            return Response(
                {'detail': 'Заголовок X-Telegram-Init-Data обязателен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = exchange_webapp_init_data(init_data)
            logger.info(
                "webapp login success",
                extra={
                    **log_extra,
                    "telegram_user_id": payload.get("telegram_user_id"),
                    "exp": payload.get("exp"),
                    "has_refresh": bool(payload.get("refresh")),
                },
            )
        except TelegramWebAppAuthError as exc:
            detail = str(exc)
            reason_code = getattr(exc, "reason", None)
            details = getattr(exc, "details", {}) or {}
            failure_extra = {**log_extra, "reason": reason_code or detail}
            if details:
                failure_extra["error_details"] = details
            if reason_code == "hash mismatch":
                failure_extra.update(
                    {
                        "hash_expected_prefix": details.get("expected_hash"),
                        "hash_received_prefix": details.get("received_hash"),
                        "base_string_len": details.get("base_string_len"),
                    }
                )
            logger.warning("webapp login failed", extra=failure_extra)
            metric_reason = _resolve_failure_reason(reason_code, parse_errors, skew_flag, init_source)
            increment_login_failure(metric_reason)

            if detail == 'initData is required':
                message = 'Заголовок X-Telegram-Init-Data обязателен'
            elif detail == 'user missing in initData':
                message = 'В initData отсутствует пользователь'
            elif detail == 'telegram id missing':
                message = 'В initData отсутствует telegram_id'
            elif detail.startswith('invalid initData:'):
                reason = detail.split(':', 1)[1].strip()
                message = f'Неверные данные WebApp: {reason}'
            else:
                message = detail
            if metric_reason == "time_skew" and skew_seconds is not None:
                details_msg = f" (возможный сдвиг времени: {round(skew_seconds, 2)}с)"
            else:
                details_msg = ""
            return Response({'detail': message + details_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.exception(
                "webapp login unexpected error",
                extra=log_extra,
            )
            increment_login_failure("unexpected_error")
            return Response(
                {'detail': f'Не удалось подтвердить данные WebApp: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload)


class WebAppRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_refresh = request.data.get('refresh')
        rid = getattr(request, "request_id", get_request_id())
        log_extra = {
            "rid": rid,
            "request_id": rid,
            "build_fingerprint": get_build_fingerprint(),
            "refresh": summarize_token(raw_refresh),
        }
        logger.info("webapp refresh request", extra=log_extra)
        if not raw_refresh:
            return Response(
                {'detail': 'Поле refresh обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_token = RefreshToken(raw_refresh)
        except TokenError as exc:
            logger.warning(
                "webapp refresh invalid",
                extra={**log_extra, "reason": str(exc) or 'invalid_refresh'},
            )
            return Response(
                {'detail': str(exc) or 'Refresh токен недействителен'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = refresh_token.get('user_id')
        if not user_id:
            logger.warning(
                "webapp refresh missing user",
                extra=log_extra,
            )
            return Response(
                {'detail': 'Refresh токен не содержит пользователя'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(
                "webapp refresh user_not_found",
                extra={**log_extra, "user_id": user_id},
            )
            return Response(
                {'detail': 'Пользователь не найден'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        profile, _ = Profile.objects.get_or_create(user=user)
        access_token = refresh_token.access_token
        exp = access_token.get('exp')
        payload = {
            'access': str(access_token),
            'refresh': str(refresh_token),
            'telegram_user_id': profile.telegram_id,
        }
        if isinstance(exp, int):
            payload['exp'] = exp

        logger.info(
            "webapp refresh success",
            extra={
                **log_extra,
                "user_id": user_id,
                "telegram_user_id": profile.telegram_id,
                "exp": payload.get('exp'),
            },
        )

        return Response(payload)
