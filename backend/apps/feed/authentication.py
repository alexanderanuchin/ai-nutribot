from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


def authenticate_integration_key(request: HttpRequest) -> None:
    expected = getattr(settings, "BOT_INTERNAL_KEY", "")
    provided = request.headers.get("X-Integration-Key") or request.headers.get("X-Bot-Key")
    if not expected or provided != expected:
        raise AuthenticationFailed("Invalid integration key")


def authenticate_access_token(token: str) -> User:
    if not token:
        raise AuthenticationFailed("Token is required")
    try:
        validated = AccessToken(token)
    except Exception as exc:  # pragma: no cover - JWT library handles specifics
        raise AuthenticationFailed("Invalid token") from exc
    user_id = validated.get("user_id")
    if not user_id:
        raise AuthenticationFailed("Invalid token payload")
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:  # pragma: no cover - defensive
        raise AuthenticationFailed("User not found") from exc


def extract_token_from_request(request: HttpRequest) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.GET.get("token")