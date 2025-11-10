"""
ASGI config for nutribot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application
from typing import Any, Mapping

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutribot.settings")

django_asgi_app = get_asgi_application()

if not settings.DEBUG:
    channel_layers = getattr(settings, "CHANNEL_LAYERS", {}) or {}
    default_layer: Mapping[str, Any]
    if isinstance(channel_layers, Mapping):
        default_layer = channel_layers.get("default", {}) or {}
    else:
        default_layer = {}
    backend_path = ""
    if isinstance(default_layer, Mapping):
        backend_path = str(default_layer.get("BACKEND", ""))
    if backend_path.endswith("InMemoryChannelLayer"):
        raise RuntimeError(
            "Redis channel layer must be configured in production. Set REDIS_URL."
        )

from apps.feed.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
