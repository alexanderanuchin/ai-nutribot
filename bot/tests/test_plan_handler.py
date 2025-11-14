from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bot.backend_client import AuthResult, BackendError, BackendValidationError
from bot.handlers.plan import (
    _poll_job_status,
    generate_plan,
    plan_topup_callback,
    resume_plan_generation_if_needed,
)
from bot.payments import parse_invoice_payload


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.current_state = None

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def clear(self):
        self.data.clear()
        self.current_state = None

    async def set_state(self, value):
        self.current_state = value

    async def get_state(self):
        return self.current_state


@pytest.mark.asyncio
async def test_generate_plan_handles_insufficient_balance(monkeypatch):
    backend = MagicMock()
    backend.create_wallet_hold = AsyncMock(side_effect=BackendValidationError({"code": "insufficient_funds"}))
    backend.generate_plan = AsyncMock()

    monkeypatch.setattr("bot.handlers.plan._make_attempt_id", lambda: 4242)

    state = FakeState(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "plan_period": 7,
            "plan_pricing": {"amount": 100, "currency": "XTR"},
        }
    )

    message = MagicMock()
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message = message

    await generate_plan(
        callback,
        backend,
        state,
        webapp_url="https://app.example",
        support_url="https://support.example",
    )

    backend.generate_plan.assert_not_called()
    assert message.answer.await_count == 1
    sent_text = message.answer.call_args[0][0]
    assert (
        sent_text
        == "Недостаточно Stars. Требуется 100 XTR. После пополнения продолжу автоматически."
    )
    pending = state.data.get("pending_action") or {}
    assert pending.get("type") == "generate_plan"
    assert pending.get("attempt_id") == 4242
    assert pending.get("status") == "awaiting_payment"
    assert pending.get("amount") == 100


@pytest.mark.asyncio
async def test_generate_plan_consumes_hold_and_renders_summary():
    backend = MagicMock()
    backend.create_wallet_hold = AsyncMock(
        return_value=AuthResult(payload={"id": 11, "amount": 100, "currency": "XTR"}, access=None, refresh=None)
    )
    backend.generate_plan = AsyncMock(
        return_value=AuthResult(
            payload={"plan_id": 55, "summary": {"period_days": 7, "daily_kcal": 2000}},
            access="new-access",
            refresh="new-refresh",
        )
    )
    backend.consume_wallet_hold = AsyncMock(return_value=AuthResult(payload={}, access=None, refresh=None))

    state = FakeState(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "plan_period": 7,
            "plan_pricing": {"amount": 100, "currency": "XTR"},
        }
    )

    message = MagicMock()
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message = message

    await generate_plan(
        callback,
        backend,
        state,
        webapp_url="https://app.example",
        support_url="https://support.example",
    )

    backend.consume_wallet_hold.assert_awaited()
    final_text = message.edit_text.call_args_list[-1][0][0]
    assert "План готов" in final_text
    assert state.data.get("access_token") == "new-access"
    assert state.data.get("refresh_token") == "new-refresh"
    assert await state.get_state() is None
    args, kwargs = backend.create_wallet_hold.call_args
    context = kwargs["context"]
    assert context["period_days"] == 7
    assert "attempt_id" in context


@pytest.mark.asyncio
async def test_resume_plan_generation_if_needed(monkeypatch):
    state = FakeState(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "pending_action": {"type": "generate_plan", "period": 14, "attempt_id": 99},
            "plan_pricing": {"amount": 200, "currency": "XTR"},
        }
    )

    message = MagicMock()
    message.answer = AsyncMock()
    progress_message = MagicMock()
    progress_message.edit_text = AsyncMock()
    message.answer.return_value = progress_message
    message.from_user = SimpleNamespace(id=42)

    backend = MagicMock()
    initiate_mock = AsyncMock()
    monkeypatch.setattr("bot.handlers.plan._initiate_plan_generation", initiate_mock)

    resumed = await resume_plan_generation_if_needed(message, backend, state, rid="rid-1")

    assert resumed is True
    initiate_mock.assert_awaited_once()
    _, kwargs = initiate_mock.call_args
    assert kwargs["backend"] is backend
    assert kwargs["state"] is state
    assert kwargs["period"] == 14
    assert kwargs["pricing"] == {"amount": 200, "currency": "XTR"}
    assert kwargs["attempt_id"] == 99
    assert kwargs["telegram_user_id"] == 42
    assert state.data.get("pending_action") is None
    message.answer.assert_awaited_once()
    assert message.answer.await_args.args[0] == "Оплата получена! Продолжаю генерацию плана…"


@pytest.mark.asyncio
async def test_plan_topup_callback_builds_invoice(monkeypatch):
    state = FakeState(
        {
            "pending_action": {
                "type": "generate_plan",
                "attempt_id": 4242,
                "status": "awaiting_payment",
                "amount": 100,
            },
        }
    )

    message = MagicMock()
    message.answer_invoice = AsyncMock()
    callback = MagicMock()
    callback.message = message
    callback.answer = AsyncMock()
    callback.from_user = SimpleNamespace(id=99)
    callback.data = "plan:topup:200"

    monkeypatch.setattr("bot.handlers.plan.get_request_id", lambda: "rid-test")

    await plan_topup_callback(
        callback,
        state,
        provider_token="provider-token",
        webapp_url="https://app.example",
        support_url="https://support.example",
    )

    message.answer_invoice.assert_awaited_once()
    invoice_kwargs = message.answer_invoice.call_args.kwargs
    assert invoice_kwargs["provider_token"] == "provider-token"
    payload_meta = parse_invoice_payload(invoice_kwargs["payload"])
    assert payload_meta["intent"] == "plan_topup"
    assert payload_meta["aid"] == "4242"
    assert payload_meta["action"] == "generate_plan"
    pending = state.data.get("pending_action")
    assert pending["status"] == "invoice_sent"


@pytest.mark.asyncio
async def test_poll_job_status_releases_hold_on_failure(monkeypatch):
    backend = MagicMock()
    backend.job_status = AsyncMock(side_effect=BackendError("boom"))
    release_mock = AsyncMock()
    monkeypatch.setattr("bot.handlers.plan._release_plan_hold", release_mock)
    message = MagicMock()
    message.edit_text = AsyncMock()
    state = FakeState()
    hold_info = {"id": 5, "amount": 120, "currency": "XTR", "action": "generate_plan", "attempt_id": 555}

    await _poll_job_status(
        message,
        backend,
        state,
        access_token="token",
        refresh_token="refresh",
        job_id="job-1",
        hold_info=hold_info,
        pricing={"amount": 120},
        rid="rid-1",
        telegram_user_id=777,
        attempt_id=555,
    )

    release_mock.assert_awaited_once()
    _, kwargs = release_mock.call_args
    assert kwargs["reason"] == "job_failed"
    assert kwargs["telegram_user_id"] == 777
    message.edit_text.assert_awaited()


@pytest.mark.asyncio
async def test_poll_job_status_times_out_and_releases_hold(monkeypatch):
    backend = MagicMock()
    backend.job_status = AsyncMock(
        return_value=AuthResult(payload={"status": "pending"}, access=None, refresh=None)
    )
    release_mock = AsyncMock()
    monkeypatch.setattr("bot.handlers.plan._release_plan_hold", release_mock)
    sleep_mock = AsyncMock(return_value=None)
    monkeypatch.setattr("bot.handlers.plan.asyncio.sleep", sleep_mock)
    message = MagicMock()
    message.edit_text = AsyncMock()
    state = FakeState()
    hold_info = {"id": 9, "amount": 200, "currency": "XTR", "action": "generate_plan", "attempt_id": 777}

    await _poll_job_status(
        message,
        backend,
        state,
        access_token="token",
        refresh_token="refresh",
        job_id="job-2",
        hold_info=hold_info,
        pricing={"amount": 200},
        rid="rid-2",
        telegram_user_id=888,
        attempt_id=777,
    )

    release_mock.assert_awaited_once()
    _, kwargs = release_mock.call_args
    assert kwargs["reason"] == "job_timeout"
    assert kwargs["telegram_user_id"] == 888
    sleep_mock.assert_awaited()
    assert any("слишком много времени" in call.args[0] for call in message.edit_text.call_args_list)
