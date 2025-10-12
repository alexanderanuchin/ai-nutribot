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

logger = logging.getLogger("audit.auth")


class WebAppLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data') or request.data.get('init_data')
        rid = request.headers.get('X-Request-Id') or request.META.get('HTTP_X_REQUEST_ID')
        logger.info(
            "webapp login request rid=%s has_init_data=%s init_data=%s",
            rid,
            bool(init_data),
            summarize_token(init_data),
        )
        if not init_data:
            return Response(
                {'detail': 'Заголовок X-Telegram-Init-Data обязателен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = exchange_webapp_init_data(init_data)
            logger.info(
                "webapp login success rid=%s telegram_user_id=%s exp=%s has_refresh=%s",
                rid,
                payload.get('telegram_user_id'),
                payload.get('exp'),
                bool(payload.get('refresh')),
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
                "webapp login failed rid=%s reason=%s",
                rid,
                message,
            )
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.exception(
                "webapp login unexpected error rid=%s", rid
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
        rid = request.headers.get('X-Request-Id') or request.META.get('HTTP_X_REQUEST_ID')
        logger.info(
            "webapp refresh request rid=%s refresh=%s",
            rid,
            summarize_token(raw_refresh),
        )
        if not raw_refresh:
            return Response(
                {'detail': 'Поле refresh обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_token = RefreshToken(raw_refresh)
        except TokenError as exc:
            logger.warning(
                "webapp refresh invalid rid=%s reason=%s",
                rid,
                str(exc) or 'invalid_refresh',
            )
            return Response(
                {'detail': str(exc) or 'Refresh токен недействителен'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = refresh_token.get('user_id')
        if not user_id:
            logger.warning(
                "webapp refresh missing user rid=%s",
                rid,
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
                "webapp refresh user_not_found rid=%s user_id=%s",
                rid,
                user_id,
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
            "webapp refresh success rid=%s user_id=%s telegram_user_id=%s exp=%s",
            rid,
            user_id,
            profile.telegram_id,
            payload.get('exp'),
        )

        return Response(payload)
