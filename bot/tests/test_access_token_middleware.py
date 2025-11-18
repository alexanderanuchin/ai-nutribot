from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.storage.memory import MemoryStorage

from bot.middlewares.access_token import AccessTokenMiddleware


class DummyState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


@pytest.mark.asyncio
async def test_middleware_uses_existing_state_token(monkeypatch):
    middleware = AccessTokenMiddleware(MemoryStorage())
    event = SimpleNamespace(from_user=SimpleNamespace(id=42), chat=SimpleNamespace(id=42))
    backend = MagicMock()
    backend.get_telegram_session = AsyncMock()

    handler = AsyncMock()

    state = DummyState({"access_token": "existing"})
    data = {"state": state, "bot": SimpleNamespace(id=1), "backend": backend}

    await middleware(handler, event, data)

    handler.assert_awaited()
    backend.get_telegram_session.assert_not_awaited()
    assert data["access_token"] == "existing"


@pytest.mark.asyncio
async def test_middleware_fetches_backend_session(monkeypatch):
    middleware = AccessTokenMiddleware(MemoryStorage())
    event = SimpleNamespace(from_user=SimpleNamespace(id=99), chat=SimpleNamespace(id=77))
    backend = MagicMock()
    backend.get_telegram_session = AsyncMock(
        return_value={"access": "fetched", "refresh": "ref", "expires_at": "2024-01-01T00:00:00Z"}
    )

    handler = AsyncMock()
    data = {"bot": SimpleNamespace(id=1), "backend": backend}

    await middleware(handler, event, data)

    backend.get_telegram_session.assert_awaited_once_with(99)
    handler.assert_awaited()
    state = data["state"]
    stored = await state.get_data()
    assert stored["access_token"] == "fetched"
    assert stored["refresh_token"] == "ref"
    assert stored["session_user_id"] == 99
    assert data["access_token"] == "fetched"
