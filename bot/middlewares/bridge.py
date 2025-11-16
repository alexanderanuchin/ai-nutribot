from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from bot.logkit import get_request_id
from bot.services.bridge import BridgePublisher

logger = logging.getLogger("audit.telegram")


class BridgeEventsMiddleware(BaseMiddleware):
    def __init__(self, publisher: BridgePublisher) -> None:
        super().__init__()
        self.publisher = publisher

    async def __call__(self, handler, event: Any, data: dict[str, Any]):
        rid = data.get("request_id") or get_request_id()
        result = await handler(event, data)
        await self._publish_event(event, rid)
        return result

    async def _publish_event(self, event: Any, rid: str) -> None:
        if not self.publisher.enabled:
            return
        message = self._extract_message(event)
        if not message or not getattr(message.from_user, "id", None):
            return
        role = "bot_message" if getattr(message.from_user, "is_bot", False) else "user_message"
        text = (getattr(message, "text", None) or getattr(message, "caption", None) or "").strip()
        if not text:
            return
        payload = {
            "id": f"tg-{getattr(message, 'message_id', 'msg')}",
            "type": role,
            "text": text[:4096],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await self.publisher.publish(message.from_user.id, payload, rid=rid)

    def _extract_message(self, event: Any) -> Message | None:
        if isinstance(event, Message):
            return event
        if isinstance(event, Update):
            if event.message:
                return event.message
            if event.callback_query and isinstance(event.callback_query, CallbackQuery):
                return event.callback_query.message
        if isinstance(event, CallbackQuery):
            return event.message
        return None
