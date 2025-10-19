from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator


@dataclass(frozen=True)
class FeedEvent:
    group_name: str
    payload: Dict[str, object]


class FeedEventBroker:
    """Simple in-memory pub/sub broker for SSE fallback."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, queue.Queue[FeedEvent]] = {}
        self._lock = threading.RLock()

    def subscribe(self) -> tuple[str, queue.Queue[FeedEvent]]:
        subscriber_id = uuid.uuid4().hex
        q: "queue.Queue[FeedEvent]" = queue.Queue(maxsize=256)
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
            except queue.Full:
                # Drop oldest event to keep connection alive
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    q.put_nowait(event)
                except queue.Full:  # pragma: no cover - highly unlikely after drop
                    pass

    def iter_events(self, queue_: "queue.Queue[FeedEvent]") -> Iterator[FeedEvent]:
        while True:
            try:
                yield queue_.get(timeout=30)
            except queue.Empty:
                # keep-alive event
                yield FeedEvent(group_name="feed.keepalive", payload={"timestamp": time.time()})


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