from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict

from aiogram import BaseMiddleware

from bot.logging_utils import get_request_id
from bot.utils.texts import THROTTLED_TEXT


class ThrottleMiddleware(BaseMiddleware):
    """Простая реализация троттлинга по user_id."""

    def __init__(self, limit: int = 3, interval: float = 10.0) -> None:
        super().__init__()
        self.limit = max(1, int(limit))
        self.interval = float(interval)
        self._buckets: Dict[int, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("bot.throttle")

    async def __call__(self, handler: Callable, event: Any, data: dict[str, Any]):
        user = data.get("event_from_user")
        user_id = getattr(user, "id", None)
        if user_id is None:
            return await handler(event, data)

        async with self._lock:
            bucket = self._buckets[user_id]
            now = time.monotonic()
            while bucket and now - bucket[0] > self.interval:
                bucket.popleft()
            if len(bucket) >= self.limit:
                rid = data.get("request_id") or get_request_id()
                self.logger.warning(
                    "throttle limit exceeded",
                    extra={"rid": rid, "user_id": user_id, "size": len(bucket)},
                )
                await self._notify_user(event)
                return
            bucket.append(now)

        return await handler(event, data)

    async def _notify_user(self, event: Any) -> None:
        message = getattr(event, "message", None)
        if message is not None:
            try:
                await message.answer(THROTTLED_TEXT)
            except Exception:
                pass
            return
        if hasattr(event, "answer"):
            try:
                await event.answer(THROTTLED_TEXT, show_alert=True)
            except TypeError:
                try:
                    await event.answer(THROTTLED_TEXT)
                except Exception:
                    pass
            except Exception:
                pass


__all__ = ["ThrottleMiddleware"]