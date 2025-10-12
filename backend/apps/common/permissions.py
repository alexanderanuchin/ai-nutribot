from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasBotKey(BasePermission):
    def has_permission(self, request, view):
        key = request.headers.get("X-Bot-Key")
        return bool(key) and (key == getattr(settings, "BOT_INTERNAL_KEY", ""))


class HasBotKeyOrIsAuthenticated(BasePermission):
    """Allow access either for the bot (internal key) or authenticated users."""

    def has_permission(self, request, view):  # pragma: no cover - thin glue
        key = request.headers.get("X-Bot-Key")
        expected = getattr(settings, "BOT_INTERNAL_KEY", "")
        if key and expected and key == expected:
            setattr(request, "_auth_component", "bot")
            return True

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            setattr(request, "_auth_component", "webapp")
            return True

        return False


__all__ = ["HasBotKey", "HasBotKeyOrIsAuthenticated"]
