from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.tg_auth import (
    TelegramWebAppAuthError,
    exchange_webapp_init_data,
)


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