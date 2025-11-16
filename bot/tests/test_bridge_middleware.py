from datetime import datetime

import pytest
from aiogram.types import Message

from bot.middlewares.bridge import BridgeEventsMiddleware
from bot.services.bridge import BridgePublisher


class DummyPublisher(BridgePublisher):
    def __init__(self):
        super().__init__(redis=None)
        self.published = []

    @property
    def enabled(self) -> bool:  # type: ignore[override]
        return True

    async def publish(self, telegram_user_id: int, event: dict, *, rid: str | None = None) -> None:  # type: ignore[override]
        self.published.append((telegram_user_id, event, rid))


def _message(text: str) -> Message:
    return Message.model_validate(
        {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": 111, "type": "private"},
            "from": {"id": 111, "is_bot": False, "first_name": "Tester"},
            "text": text,
        }
    )


@pytest.mark.asyncio
async def test_bridge_middleware_publishes_user_message():
    publisher = DummyPublisher()
    middleware = BridgeEventsMiddleware(publisher)
    message = _message("Привет")

    async def _handler(e, d):
        return "ok"

    result = await middleware(_handler, message, {})

    assert result == "ok"
    assert len(publisher.published) == 1
    user_id, event, rid = publisher.published[0]
    assert user_id == 111
    assert event["type"] == "user_message"
    assert event["text"] == "Привет"
    assert rid


@pytest.mark.asyncio
async def test_bridge_middleware_skips_empty_text():
    publisher = DummyPublisher()
    middleware = BridgeEventsMiddleware(publisher)
    message = _message("")

    async def _handler(e, d):
        return None

    await middleware(_handler, message, {})

    assert not publisher.published
