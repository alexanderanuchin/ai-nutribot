from typing import Any, Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .api_payloads import build_profile_response
from .tg_utils import verify_init_data

from .models import Profile

User = get_user_model()

try:  # pragma: no cover - depends on project configuration
    User._meta.get_field("telegram_id")
    USER_HAS_TELEGRAM_FIELD = True
except FieldDoesNotExist:  # pragma: no cover - default local setup
    USER_HAS_TELEGRAM_FIELD = False


def _ensure_profile_telegram_id(user, tg_id: int) -> None:
    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.telegram_id != tg_id:
        profile.telegram_id = tg_id
        profile.save(update_fields=["telegram_id"])


@transaction.atomic
def _get_user_by_telegram_id(tg_id: int, username: str):
    """Return user bound to the Telegram id, creating a link if needed."""

    if USER_HAS_TELEGRAM_FIELD:
        user, created = User.objects.get_or_create(
            telegram_id=tg_id, defaults={"username": username}
        )
        if getattr(user, "telegram_id", None) != tg_id:
            user.telegram_id = tg_id
            user.save(update_fields=["telegram_id"])
        _ensure_profile_telegram_id(user, tg_id)
        return user, created

    profile = (
        Profile.objects.select_related("user").filter(telegram_id=tg_id).first()
    )
    if profile:
        return profile.user, False

    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    _ensure_profile_telegram_id(user, tg_id)
    return user, created


class TelegramWebAppAuthError(Exception):
    """Raised when Telegram WebApp initData validation fails."""


def exchange_webapp_init_data(
        init_data: str | None,
        *,
        bot_token: str | None = None,
) -> Dict[str, Any]:
    if not init_data:
        raise TelegramWebAppAuthError("initData is required")

    token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    try:
        parsed = verify_init_data(init_data, token)
    except Exception as exc:  # pragma: no cover - depends on Telegram payload
        raise TelegramWebAppAuthError(f"invalid initData: {exc}") from exc

    user_json = parsed.get("user")
    if not user_json:
        if not isinstance(user_json, dict):
            raise TelegramWebAppAuthError("user missing in initData")

    tg_id = user_json.get("id")
    if not tg_id:
        raise TelegramWebAppAuthError("telegram id missing")

    username = str(user_json.get("username") or f"tg_{tg_id}")
    user, created = _get_user_by_telegram_id(int(tg_id), username)
    if created:
        user.first_name = user_json.get("first_name") or ""
        user.last_name = user_json.get("last_name") or ""
        user.save(update_fields=["first_name", "last_name"])

    profile = Profile.objects.select_related("user").get(user=user)
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    exp = access_token.get("exp")
    payload = build_profile_response(user, profile)
    payload.update(
        {
            "access": str(access_token),
            "refresh": str(refresh),
            "telegram_user_id": profile.telegram_id,
            "exp": int(exp) if isinstance(exp, int) else exp,
        }
    )
    return payload


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
    return Response(payload)
