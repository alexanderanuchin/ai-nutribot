from rest_framework.permissions import BasePermission
from django.conf import settings

class HasBotKey(BasePermission):
    def has_permission(self, request, view):
        key = request.headers.get("X-Bot-Key")
        return bool(key) and (key == getattr(settings, "BOT_INTERNAL_KEY", ""))
