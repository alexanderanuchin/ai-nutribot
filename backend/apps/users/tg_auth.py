from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .tg_utils import verify_init_data

User = get_user_model()

@api_view(["POST"])
@permission_classes([AllowAny])
def tg_exchange(request):
    """
    Body: { "init_data": "<raw initData from Telegram WebApp>" }
    """
    init_data = request.data.get("init_data")
    try:
        parsed = verify_init_data(init_data, getattr(settings, "TELEGRAM_BOT_TOKEN", ""))
    except Exception as e:
        return Response({"detail": f"invalid initData: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    user_json = parsed.get("user")
    if not user_json:
        return Response({"detail": "user missing in initData"}, status=status.HTTP_400_BAD_REQUEST)

    tg_id = user_json.get("id")
    if not tg_id:
        return Response({"detail": "telegram id missing"}, status=status.HTTP_400_BAD_REQUEST)

    # Найдём/создадим пользователя по telegram_id
    username = f"tg_{tg_id}"
    user, created = User.objects.get_or_create(telegram_id=tg_id, defaults={"username": username})
    if created and "first_name" in user_json:
        user.first_name = user_json.get("first_name") or ""
        user.last_name  = user_json.get("last_name") or ""
        user.save(update_fields=["first_name","last_name"])

    refresh = RefreshToken.for_user(user)
    return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
