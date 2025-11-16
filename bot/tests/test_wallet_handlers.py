from __future__ import annotations

from pathlib import Path
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bot.backend_client import AuthResult, BackendNetworkError
from bot.constants import STARS_BLOCKED_MESSAGE
from bot.handlers.wallet import (
    MAX_TOPUP_AMOUNT,
    MIN_TOPUP_AMOUNT,
    bot_stars_command,
    pre_checkout_handler,
    successful_payment_handler,
    wallet_command,
    wallet_topup_callback,
)


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
async def test_wallet_command_success():
    backend = MagicMock()
    backend.get_my_stars = AsyncMock(
        return_value=AuthResult(
            payload={
                "balance": {"amount": 120, "currency": "XTR"},
                "transactions": [
                    {"direction": "in", "amount": 50, "occurred_at": "2024-01-01T10:00:00"}
                ],
            },
            access="new-token",
            refresh="new-refresh",
        )
    )
    state = FakeState({"refresh_token": "refresh"})
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=123)

    await wallet_command(message, backend, state, access_token="access", webapp_url="https://example.com")

    backend.get_my_stars.assert_awaited()
    assert state.data["access_token"] == "new-token"
    assert state.data["refresh_token"] == "new-refresh"
    assert state.data.get("stars_purchase_blocked") is False
    args, kwargs = message.answer.call_args
    assert "Ваш баланс" in args[0]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_wallet_command_network_retry():
    backend = MagicMock()
    backend.get_my_stars = AsyncMock(
        side_effect=[
            BackendNetworkError("timeout"),
            AuthResult(payload={"balance": {"amount": 0, "currency": "XTR"}, "transactions": []}, access="a", refresh="r"),
        ]
    )
    state = FakeState({"refresh_token": "refresh"})
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)

    await wallet_command(message, backend, state, access_token="access", webapp_url="https://example.com")

    assert backend.get_my_stars.await_count == 2
    first_call_args = message.answer.call_args_list[0][0][0]
    assert "пробую ещё раз" in first_call_args


@pytest.mark.asyncio
async def test_wallet_command_requires_auth():
    backend = MagicMock()
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)
    state = FakeState()

    await wallet_command(message, backend, state, access_token=None, webapp_url="https://example.com")

    message.answer.assert_awaited()
    text = message.answer.call_args[0][0]
    markup = message.answer.call_args[1]["reply_markup"]
    assert "авториз" in text.lower()
    assert getattr(markup, "keyboard", None)


@pytest.mark.asyncio
async def test_wallet_topup_callback_sends_invoice():
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.data = "wallet:topup:100"
    callback.from_user = SimpleNamespace(id=5)
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.answer_invoice = AsyncMock()

    state = FakeState({"access_token": "token"})

    await wallet_topup_callback(
        callback,
        state,
        access_token=None,
        webapp_url="https://example.com",
        provider_token="provider",
    )

    callback.message.answer_invoice.assert_awaited()
    kwargs = callback.message.answer_invoice.call_args.kwargs
    assert kwargs["currency"] == "XTR"
    assert kwargs["prices"][0].amount == 100
    assert kwargs["prices"][0].label == "Пополнение 100 XTR"
    assert kwargs["provider_token"] == "provider"
    assert "max_tip_amount" not in kwargs
    callback.answer.assert_awaited()


@pytest.mark.asyncio
async def test_wallet_topup_callback_includes_plan_payload(monkeypatch):
    monkeypatch.setattr("bot.handlers.wallet.get_request_id", lambda: "rid-1")
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.data = "wallet:topup:200"
    callback.from_user = SimpleNamespace(id=9)
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.answer_invoice = AsyncMock()

    state = FakeState(
        {
            "access_token": "token",
            "pending_action": {
                "type": "generate_plan",
                "period": 7,
                "attempt_id": 5150,
                "status": "awaiting_payment",
            },
        }
    )

    await wallet_topup_callback(
        callback,
        state,
        access_token=None,
        webapp_url="https://example.com",
        provider_token="provider",
    )

    payload = callback.message.answer_invoice.call_args.kwargs["payload"]
    assert "intent=plan_topup" in payload
    assert "aid=5150" in payload
    assert state.data["pending_action"]["status"] == "invoice_sent"


@pytest.mark.asyncio
async def test_wallet_topup_callback_requires_auth_before_invoice():
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.data = "wallet:topup:100"
    callback.from_user = SimpleNamespace(id=5)
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.answer_invoice = AsyncMock()

    state = FakeState()

    await wallet_topup_callback(
        callback,
        state,
        access_token=None,
        webapp_url="https://example.com",
        provider_token=None,
    )

    callback.message.answer.assert_awaited()
    text = callback.message.answer.call_args[0][0]
    assert "авториз" in text.lower()
    callback.message.answer_invoice.assert_not_called()
    callback.answer.assert_awaited()


@pytest.mark.asyncio
async def test_wallet_topup_callback_respects_blocked():
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.data = "wallet:topup:100"
    callback.from_user = SimpleNamespace(id=5)
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.answer_invoice = AsyncMock()

    state = FakeState({"access_token": "token", "stars_purchase_blocked": True})

    await wallet_topup_callback(
        callback,
        state,
        access_token=None,
        webapp_url="https://example.com",
        provider_token=None,
    )

    callback.message.answer.assert_awaited()
    text = callback.message.answer.call_args[0][0]
    assert text == STARS_BLOCKED_MESSAGE
    callback.message.answer_invoice.assert_not_called()
    callback.answer.assert_awaited()


@pytest.mark.asyncio
async def test_pre_checkout_rejects_amount_below_min():
    query = MagicMock()
    query.answer = AsyncMock()
    query.from_user = SimpleNamespace(id=MIN_TOPUP_AMOUNT)
    query.currency = "XTR"
    query.total_amount = MIN_TOPUP_AMOUNT - 1
    query.invoice_payload = f"uid={MIN_TOPUP_AMOUNT};amt={MIN_TOPUP_AMOUNT - 1};token=abc"

    await pre_checkout_handler(query)

    query.answer.assert_awaited()
    kwargs = query.answer.call_args.kwargs
    assert kwargs["ok"] is False
    assert "миним" in kwargs["error_message"].lower()


@pytest.mark.asyncio
async def test_pre_checkout_rejects_amount_above_max():
    query = MagicMock()
    query.answer = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    query.currency = "XTR"
    query.total_amount = MAX_TOPUP_AMOUNT + 1
    query.invoice_payload = f"uid=1;amt={MAX_TOPUP_AMOUNT + 1};token=abc"

    await pre_checkout_handler(query)

    query.answer.assert_awaited()
    kwargs = query.answer.call_args.kwargs
    assert kwargs["ok"] is False
    assert "больш" in kwargs["error_message"].lower()


@pytest.mark.asyncio
async def test_successful_payment_handler_records_topup():
    backend = MagicMock()
    backend.report_stars_payment = AsyncMock()
    state = FakeState({"refresh_token": "refresh"})
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)
    payment = SimpleNamespace(
        telegram_payment_charge_id="charge123",
        provider_payment_charge_id=None,
        total_amount=50,
        currency="XTR",
        invoice_payload="uid=1;amt=50;token=abc;aid=77",
    )
    message.successful_payment = payment

    await successful_payment_handler(message, backend, state, access_token="token")

    backend.report_stars_payment.assert_awaited()
    kwargs = backend.report_stars_payment.call_args.kwargs
    assert kwargs["amount"] == 50
    assert kwargs["charge_id"] == "charge123"
    assert kwargs["payment_attempt_id"] == 77
    message.answer.assert_awaited()
    assert any("Баланс пополнен" in call.args[0] for call in message.answer.call_args_list)


@pytest.mark.asyncio
async def test_successful_payment_handler_triggers_plan_resume(monkeypatch):
    backend = MagicMock()
    backend.report_stars_payment = AsyncMock()
    state = FakeState(
        {
            "refresh_token": "refresh",
            "pending_action": {
                "type": "generate_plan",
                "period": 10,
                "attempt_id": 321,
                "status": "awaiting_payment",
            },
        }
    )
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=7)
    payment = SimpleNamespace(
        telegram_payment_charge_id="charge777",
        provider_payment_charge_id=None,
        total_amount=200,
        currency="XTR",
        invoice_payload="uid=7;amt=200;token=abc;intent=plan_topup;aid=321;action=generate_plan",
    )
    message.successful_payment = payment

    resume_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.handlers.wallet.resume_plan_generation_if_needed", resume_mock)

    await successful_payment_handler(message, backend, state, access_token="token")

    resume_mock.assert_awaited_once()
    args, kwargs = resume_mock.call_args
    assert args[0] is message
    assert args[1] is backend
    assert args[2] is state
    assert "rid" in kwargs and kwargs["rid"]
    assert kwargs["attempt_id"] == 321
    assert kwargs["intent"] == "plan_topup"
    message.answer.assert_not_awaited()

@pytest.mark.asyncio
async def test_bot_stars_command_requires_admin():
    backend = MagicMock()
    state = FakeState()
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)

    await bot_stars_command(message, backend, state, access_token="token", admin_ids=(2, 3))

    message.answer.assert_awaited()
    text = message.answer.call_args[0][0]
    assert "администрато" in text.lower()


@pytest.mark.asyncio
async def test_bot_stars_command_success():
    backend = MagicMock()
    backend.get_bot_stars_balance = AsyncMock(
        return_value=AuthResult(payload={"balance": {"amount": 321, "currency": "XTR", "updated_at": "2024-01-02"}}, access="a", refresh="r")
    )
    state = FakeState({"refresh_token": "refresh"})
    message = MagicMock()
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=42)

    await bot_stars_command(message, backend, state, access_token="token", admin_ids=(42,))

    backend.get_bot_stars_balance.assert_awaited()
    args = message.answer.call_args[0][0]
    assert "Баланс бота" in args