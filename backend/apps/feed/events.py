from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Iterable, Iterator, Mapping, Protocol

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class HasFeedIdentifiers(Protocol):
    source_id: object
    id: object


@dataclass(frozen=True)
class FeedEvent:
    group_name: str
    payload: Mapping[str, object]


class FeedEventBroker:
    """Simple in-memory pub/sub broker for SSE fallback."""

    def __init__(self) -> None:
        self._subscribers: dict[str, Queue[FeedEvent]] = {}
        self._lock = threading.RLock()

    def subscribe(self) -> tuple[str, Queue[FeedEvent]]:
        subscriber_id = uuid.uuid4().hex
        q: Queue[FeedEvent] = Queue(maxsize=256)
        with self._lock:
            self._subscribers[subscriber_id] = q
        return subscriber_id, q

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def publish(self, event: FeedEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers.values())
        for q in subscribers:
            try:
                q.put_nowait(event)
            except Full:
                # Drop oldest event to keep connection alive
                try:
                    q.get_nowait()
                except Empty:
                    pass
                try:
                    q.put_nowait(event)
                except Full:  # pragma: no cover - highly unlikely after drop
                    pass

    def iter_events(self, queue_: Queue[FeedEvent]) -> Iterator[FeedEvent]:
        while True:
            try:
                yield queue_.get(timeout=30)
            except Empty:
                # keep-alive event
                yield FeedEvent(
                    group_name="feed.keepalive",
                    payload={"timestamp": time.time()},
                )


_broker: FeedEventBroker | None = None


def get_event_broker() -> FeedEventBroker:
    global _broker
    if _broker is None:
        _broker = FeedEventBroker()
    return _broker


def format_sse(event: FeedEvent) -> Iterable[bytes]:
    data = json.dumps(event.payload, ensure_ascii=False)
    yield f"event: {event.group_name}\n".encode("utf-8")
    yield f"data: {data}\n\n".encode("utf-8")


def publish_feed_event(event: FeedEvent) -> None:
    broker = get_event_broker()
    broker.publish(event)
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        event.group_name,
        {
            "type": "feed.event",
            "event": event.payload,
            "group": event.group_name,
        },
    )


def publish_news_article_event(
    article: HasFeedIdentifiers, action: str, *, rid: str | None = None
) -> None:
    from nutribot.middleware import get_request_id

    from .serializers import NewsArticleEventSerializer

    serializer = NewsArticleEventSerializer(article)
    resolved_rid = rid or getattr(article, "ingestion_rid", None) or get_request_id()
    payload: dict[str, object] = {
        "action": action,
        "article": dict(serializer.data),
        "meta": {
            "rid": resolved_rid,
            "source_id": article.source_id,
            "article_id": article.id,
        },
    }
    event = FeedEvent(group_name="feed.news", payload=payload)
    publish_feed_event(event)
