from __future__ import annotations

import os
import re
import sys
import types

os.environ["DJANGO_DEBUG"] = "1"
os.environ.setdefault("USE_SQLITE", "1")

if "daphne" not in sys.modules:
    daphne_stub = types.ModuleType("daphne")
    testing_stub = types.ModuleType("daphne.testing")

    class _DummyDaphneProcess:  # pragma: no cover - safety net for stub
        def __init__(self, *args, **kwargs):
            raise RuntimeError("DaphneProcess stub should not be instantiated in tests")

    testing_stub.DaphneProcess = _DummyDaphneProcess
    daphne_stub.testing = testing_stub
    sys.modules["daphne"] = daphne_stub
    sys.modules["daphne.testing"] = testing_stub

import pytest
from asgiref.sync import sync_to_async
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.urls.resolvers import RegexPattern
from rest_framework_simplejwt.tokens import AccessToken

from apps.feed.routing import websocket_urlpatterns


pytestmark = pytest.mark.django_db(transaction=True)


def _get_websocket_regex() -> re.Pattern[str]:
    pattern = websocket_urlpatterns[0]
    assert isinstance(pattern.pattern, RegexPattern)
    return pattern.pattern.regex


def test_feed_websocket_route_accepts_trailing_slash() -> None:
    regex = _get_websocket_regex()
    assert regex.fullmatch("ws/feed/") is not None
    assert regex.fullmatch("/ws/feed/") is not None


def test_feed_websocket_route_accepts_without_trailing_slash() -> None:
    regex = _get_websocket_regex()
    assert regex.fullmatch("ws/feed") is not None
    assert regex.fullmatch("/ws/feed") is not None


@pytest.mark.asyncio
async def test_feed_websocket_accepts_valid_token() -> None:
    user_model = get_user_model()
    user = await sync_to_async(user_model.objects.create_user)(
        username="feed-test-user",
        email="feed-test@example.com",
        password="feed-pass",
    )
    token = AccessToken.for_user(user)

    application = ProtocolTypeRouter(
        {
            "websocket": AllowedHostsOriginValidator(
                AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            )
        }
    )

    communicator = WebsocketCommunicator(
        application,
        f"/ws/feed/?token={token}&type=news",
        headers=[(b"origin", b"http://localhost")],
    )
    try:
        connected, _ = await communicator.connect()
        assert connected is True

        initial = await communicator.receive_json_from()
        assert initial["type"] == "connected"
        assert initial["group"] == "news"
    finally:
        await communicator.disconnect()
