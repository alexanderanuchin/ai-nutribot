from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator, Iterator, Sequence
from typing import Any

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.encoding import force_str
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from apps.common.renderers import EventStreamRenderer
from apps.feed.authentication import authenticate_access_token, extract_token_from_request
from apps.feed.events import FeedEvent, format_sse, get_event_broker
from nutribot.middleware import get_request_id

logger = logging.getLogger(__name__)

# Supported marketplace resources and their event group names
RESOURCE_TO_GROUP = {
    "recipes": "market.recipes",
    "products": "market.products",
    "stores": "market.stores",
}
DEFAULT_GROUPS: Sequence[str] = tuple(RESOURCE_TO_GROUP.values())
KEEPALIVE_EVENT = "market.keepalive"


def _ensure_bytes_chunks(chunks: object) -> Iterator[bytes]:
    """Coerce an arbitrary formatter output into a byte iterator."""

    if chunks is None:
        return iter(())
    if isinstance(chunks, bytes | bytearray | memoryview):
        return iter((bytes(chunks),))
    if isinstance(chunks, str):
        return iter((chunks.encode("utf-8"),))

    try:
        iterator = iter(chunks)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("SSE formatter returned non-iterable result") from exc

    def _generator() -> Iterator[bytes]:
        for chunk in iterator:
            if chunk is None:
                continue
            if isinstance(chunk, bytes | bytearray | memoryview):
                yield bytes(chunk)
                continue
            if isinstance(chunk, str):
                yield chunk.encode("utf-8")
                continue
            raise TypeError(f"Invalid SSE chunk type: {type(chunk)!r}")

    return _generator()


def _fallback_sse(event: FeedEvent) -> Iterator[bytes]:
    event_name = force_str(getattr(event, "group_name", KEEPALIVE_EVENT) or KEEPALIVE_EVENT)
    payload: Any = getattr(event, "payload", {}) or {}
    data = json.dumps(payload, ensure_ascii=False)
    return iter(
        (
            f"event: {event_name}\n".encode(),
            f"data: {data}\n\n".encode(),
        )
    )


def _emit_sse(event: FeedEvent, *, rid: str, user_id: int) -> Iterator[bytes]:
    try:
        chunks = format_sse(event)
    except Exception as exc:
        logger.error(
            "market events: formatter raised",
            extra={"rid": rid, "error": str(exc), "user_id": user_id},
            exc_info=True,
        )
        yield from _fallback_sse(event)
        return

    try:
        iterator = _ensure_bytes_chunks(chunks)
    except Exception as exc:
        logger.error(
            "market events: formatter produced invalid chunks",
            extra={
                "rid": rid,
                "error": str(exc),
                "user_id": user_id,
                "event": force_str(getattr(event, "group_name", KEEPALIVE_EVENT)),
            },
            exc_info=True,
        )
        yield from _fallback_sse(event)
        return

    try:
        for chunk in iterator:
            yield chunk
    except Exception as exc:
        logger.error(
            "market events: formatter iteration failed",
            extra={
                "rid": rid,
                "error": str(exc),
                "user_id": user_id,
                "event": force_str(getattr(event, "group_name", KEEPALIVE_EVENT)),
            },
            exc_info=True,
        )
        for chunk in _fallback_sse(event):
            yield chunk


def _resolve_groups(resource_param: str | None) -> list[str]:
    if not resource_param:
        return list(DEFAULT_GROUPS)
    resource = resource_param.strip().lower()
    group = RESOURCE_TO_GROUP.get(resource)
    if group is None:
        raise ValueError("unsupported")
    return [group]


def _market_event_stream(
    *, groups: Sequence[str], user_id: int, rid: str
) -> Generator[bytes, None, None]:
    """Yield Server-Sent Events for given broker groups and user.
    This function is careful to never raise inside the generator to avoid 500s.
    """
    # Inform client that connection is alive
    yield b":ok\n\n"
    keepalive_event = FeedEvent(group_name=KEEPALIVE_EVENT, payload={})
    for chunk in _emit_sse(keepalive_event, rid=rid, user_id=user_id):
        yield chunk

    broker = None
    subscriber_id: str | None = None
    queue = None
    try:
        broker = get_event_broker()
        subscriber_id, queue = broker.subscribe()
        allowed_groups = set(groups)
        # Stream events
        for event in broker.iter_events(queue):
            try:
                raw_group = getattr(event, "group_name", None) or getattr(event, "group", None)
                payload = getattr(event, "payload", {}) or {}
                event_name = force_str(raw_group) if raw_group else KEEPALIVE_EVENT
                if event_name == "feed.keepalive":
                    event_name = KEEPALIVE_EVENT
                if (
                    allowed_groups
                    and event_name not in allowed_groups
                    and event_name != KEEPALIVE_EVENT
                ):
                    continue
                formatted = FeedEvent(group_name=event_name, payload=payload)
                for chunk in _emit_sse(formatted, rid=rid, user_id=user_id):
                    yield chunk
            except Exception as exc:
                logger.warning(
                    "market events: failed to format event",
                    extra={"rid": rid, "error": str(exc), "user_id": user_id},
                    exc_info=True,
                )
    except Exception as exc:
        # If broker fails (e.g., not configured), downgrade to periodic keepalives
        logger.error(
            "market events: broker unavailable",
            extra={"rid": rid, "error": str(exc), "user_id": user_id},
            exc_info=True,
        )
        while True:
            time.sleep(15)
            for chunk in _emit_sse(keepalive_event, rid=rid, user_id=user_id):
                yield chunk
    finally:
        try:
            if broker and subscriber_id is not None:
                broker.unsubscribe(subscriber_id)
        except Exception as exc:  # pragma: no cover - defensive cleanup
            logger.debug(
                "market events: unsubscribe failed",
                extra={
                    "rid": rid,
                    "error": str(exc),
                    "user_id": user_id,
                    "subscriber_id": subscriber_id,
                },
            )


class MarketEventStreamView(APIView):
    """SSE endpoint for marketplace realtime events.

    Usage (browser EventSource):
        GET /api/v1/market/events/?token=<JWT>&resource=recipes
    """
    permission_classes = [AllowAny]  # We'll authenticate manually using the ?token param
    renderer_classes = [EventStreamRenderer, JSONRenderer]

    def get(self, request: HttpRequest) -> HttpResponse:
        # 1) Authenticate from query/header
        rid = getattr(request, "request_id", get_request_id())
        token = extract_token_from_request(request)
        if not token:
            logger.info("market events: missing access token", extra={"rid": rid})
            raise PermissionDenied("Authentication required")
        try:
            user = authenticate_access_token(token)
        except AuthenticationFailed as exc:
            logger.info("market events: invalid token", extra={"rid": rid, "error": str(exc)})
            raise PermissionDenied("Authentication required") from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.info(
                "market events: token validation error",
                extra={"rid": rid, "error": str(exc)},
            )
            raise PermissionDenied("Authentication required") from exc

        # 2) Resolve target event groups
        resource_param = request.GET.get("resource")
        try:
            groups = _resolve_groups(resource_param)
        except ValueError:
            logger.info(
                "market events: unsupported resource",
                extra={"rid": rid, "resource": resource_param or ""},
            )
            raise ValidationError({"resource": "Unsupported resource"})

        # 3) Build streaming response
        user_id = getattr(user, "id", 0)
        stream = _market_event_stream(groups=groups, user_id=user_id, rid=rid)
        response = StreamingHttpResponse(
            stream,
            content_type="text/event-stream; charset=utf-8",
            status=200,
        )
        # Hardening / buffering control for proxies
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
