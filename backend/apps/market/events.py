from __future__ import annotations

from typing import Any, Mapping

from django.utils.module_loading import import_string

from apps.feed.events import FeedEvent, publish_feed_event
from nutribot.middleware import get_request_id


def _resolve_rid(context: Mapping[str, Any] | None = None) -> str:
    if context is None:
        return get_request_id()
    request = context.get("request") if isinstance(context, Mapping) else None
    if request is not None:
        return getattr(request, "request_id", get_request_id())
    rid = context.get("rid") if isinstance(context, Mapping) else None
    return rid or get_request_id()


def publish_market_event(group: str, payload: dict[str, Any], *, context: Mapping[str, Any] | None = None) -> None:
    resolved_rid = _resolve_rid(context)
    payload.setdefault("meta", {})
    payload["meta"].setdefault("rid", resolved_rid)
    event = FeedEvent(group_name=f"market.{group}", payload=payload)
    publish_feed_event(event)


def serialize_instance(instance: Any, serializer_path: str) -> dict[str, Any]:
    serializer_class = import_string(serializer_path)
    serializer = serializer_class(instance)
    return serializer.data