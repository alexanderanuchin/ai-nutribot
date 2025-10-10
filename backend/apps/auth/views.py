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


class WebAppLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        init_data = request.headers.get('X-Telegram-Init-Data') or request.data.get('init_data')
        if not init_data:
            return Response(
                {'detail': 'Заголовок X-Telegram-Init-Data обязателен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = exchange_webapp_init_data(init_data)
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
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - unexpected errors
            return Response(
                {'detail': f'Не удалось подтвердить данные WebApp: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload)


class WebAppRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_refresh = request.data.get('refresh')
        if not raw_refresh:
            return Response(
                {'detail': 'Поле refresh обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_token = RefreshToken(raw_refresh)
        except TokenError as exc:
            return Response(
                {'detail': str(exc) or 'Refresh токен недействителен'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = refresh_token.get('user_id')
        if not user_id:
            return Response(
                {'detail': 'Refresh токен не содержит пользователя'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
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

        return Response(payload)
