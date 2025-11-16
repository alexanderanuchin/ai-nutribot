from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from bot.logkit import get_request_id

logger = logging.getLogger("audit.telegram")

_EVENT_TTL_SECONDS = 3600
_EVENT_LIMIT = 50


class BridgePublisher:
    def __init__(self, redis: Redis | None) -> None:
        self._redis = redis

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    async def publish(self, telegram_user_id: int, event: dict[str, Any], *, rid: str | None = None) -> None:
        if not self._redis:
            return
        request_id = rid or get_request_id()
        payload = json.dumps(event)
        list_key = f"telegram_bridge_events:{telegram_user_id}"
        channel = f"telegram_bridge:user:{telegram_user_id}"
        try:
            pipe = self._redis.pipeline()
            pipe.rpush(list_key, payload)
            pipe.ltrim(list_key, -_EVENT_LIMIT, -1)
            pipe.expire(list_key, _EVENT_TTL_SECONDS)
            pipe.publish(channel, payload)
            await pipe.execute()
        except RedisError as exc:  # pragma: no cover - non-critical telemetry
            logger.warning(
                "bridge publish failed",
                extra={"rid": request_id, "telegram_user_id": telegram_user_id, "error": str(exc)},
            )

    async def emit_message(self, telegram_user_id: int, *, text: str | None, role: str, rid: str | None = None) -> None:
        payload = {
            "id": f"tg-{telegram_user_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "type": role,
            "text": (text or "")[:4096],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await self.publish(telegram_user_id, payload, rid=rid)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
