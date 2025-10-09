import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers.webapp_data import webapp_data_handler


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def clear(self):
        self.data.clear()


@pytest.mark.asyncio
async def test_webapp_data_handler_stores_auth_session():
    state = FakeState()
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=123)
    payload = {
        "type": "auth",
        "access_token": "token-123",
        "user_id": 123,
    }
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token=None)

    assert state.data["access_token"] == "token-123"
    assert state.data["session_user_id"] == 123
    assert "session_obtained_at" in state.data
    message.answer.assert_awaited()
    message.answer_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_requires_auth_for_topup():
    state = FakeState()
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=777)
    payload = {
        "type": "topup",
        "amount": 50,
    }
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token=None)

    message.answer.assert_awaited()
    text = message.answer.call_args[0][0]
    assert "авториз" in text.lower()
    message.answer_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_sends_invoice_on_topup():
    state = FakeState({"access_token": "token", "session_user_id": 42})
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=42)
    payload = {
        "type": "topup",
        "amount": 150,
        "comment": "За план питания",
    }
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token="token")

    message.answer_invoice.assert_awaited()
    kwargs = message.answer_invoice.call_args.kwargs
    assert kwargs["currency"] == "XTR"
    assert kwargs["prices"][0].amount == 150
    assert "Комментарий" in kwargs["description"]
    message.answer.assert_not_called()