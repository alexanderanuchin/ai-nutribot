import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.tg_auth import (
    TelegramWebAppAuthError,
    exchange_webapp_init_data,
)
from apps.users.models import Profile
from apps.common.logging import summarize_token
from nutribot.middleware import get_request_id

logger = logging.getLogger("audit.auth")


class WebAppLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data') or request.data.get('init_data')
        rid = getattr(request, "request_id", get_request_id())
        log_extra = {
            "rid": rid,
            "request_id": rid,
            "has_init_data": bool(init_data),
            "init_data": summarize_token(init_data),
        }
        logger.info("webapp login request", extra=log_extra)
        if not init_data:
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
            logger.warning(
                "webapp login failed",
                extra={**log_extra, "reason": message},
            )
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.exception(
                "webapp login unexpected error",
                extra=log_extra,
            )
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
