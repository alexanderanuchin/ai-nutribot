import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiogram.types import ReplyKeyboardRemove

from bot.handlers.wallet import MIN_TOPUP_AMOUNT
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
        "refresh_token": "refresh-456",
        "expires_at": 999999,
        "user_id": 123,
    }
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token=None, provider_token="")

    assert state.data["access_token"] == "token-123"
    assert state.data["refresh_token"] == "refresh-456"
    assert state.data["session_expires_at"] == 999999
    assert state.data["session_user_id"] == 123
    assert "session_obtained_at" in state.data
    message.answer.assert_awaited()
    kwargs = message.answer.call_args.kwargs
    assert isinstance(kwargs.get("reply_markup"), ReplyKeyboardRemove)
    message.answer_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_accepts_exp_key():
    state = FakeState()
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=321)
    payload = {
        "type": "auth",
        "access_token": "token-abc",
        "exp": 111111,
    }
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token=None, provider_token="")

    assert state.data["session_expires_at"] == 111111
    message.answer.assert_awaited()


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

    await webapp_data_handler(message, state, access_token=None, provider_token="")

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

    await webapp_data_handler(message, state, access_token="token", provider_token="")

    message.answer_invoice.assert_awaited()
    kwargs = message.answer_invoice.call_args.kwargs
    assert kwargs["currency"] == "XTR"
    assert kwargs["prices"][0].amount == 150
    assert kwargs["provider_token"] == ""
    assert "Комментарий" in kwargs["description"]
    message.answer.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_includes_plan_payload():
    state = FakeState(
        {
            "access_token": "token",
            "session_user_id": 99,
            "pending_action": {
                "type": "generate_plan",
                "period": 7,
                "attempt_id": 8888,
                "status": "awaiting_payment",
            },
        }
    )
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=99)
    payload = {"type": "topup", "amount": 120}
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token="token", provider_token="prov")

    invoice_payload = message.answer_invoice.call_args.kwargs["payload"]
    assert "intent=plan_topup" in invoice_payload
    assert "aid=8888" in invoice_payload
    assert state.data["pending_action"]["status"] == "invoice_sent"


@pytest.mark.asyncio
async def test_webapp_data_handler_rejects_invalid_json():
    state = FakeState()
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=42)
    message.web_app_data = SimpleNamespace(data="{invalid json}")

    await webapp_data_handler(message, state, access_token=None, provider_token="")

    message.answer.assert_awaited()
    message.answer_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_respects_blocked_flag():
    state = FakeState({"access_token": "token", "session_user_id": 42, "stars_purchase_blocked": True})
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=42)
    payload = {"type": "topup", "amount": 90}
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token="token", provider_token="")

    message.answer.assert_awaited()
    text = message.answer.call_args[0][0]
    assert "отключ" in text.lower()
    message.answer_invoice.assert_not_called()


@pytest.mark.asyncio
async def test_webapp_data_handler_rejects_amount_below_min():
    state = FakeState({"access_token": "token", "session_user_id": 42})
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_invoice = AsyncMock()
    message.from_user = SimpleNamespace(id=42)
    payload = {"type": "topup", "amount": MIN_TOPUP_AMOUNT - 1}
    message.web_app_data = SimpleNamespace(data=json.dumps(payload))

    await webapp_data_handler(message, state, access_token="token", provider_token="")

    message.answer.assert_awaited()
    text = message.answer.call_args[0][0]
    assert "миним" in text.lower()
    message.answer_invoice.assert_not_called()