from __future__ import annotations

import logging
import time
from typing import Generator, List, Optional, Sequence

from django.http import StreamingHttpResponse, HttpRequest, HttpResponse
from django.utils.encoding import force_str

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from apps.feed.authentication import extract_token_from_request, authenticate_access_token
from apps.feed.events import get_event_broker, format_sse

logger = logging.getLogger(__name__)

# Supported marketplace resources and their event group names
RESOURCE_TO_GROUP = {
    "recipes": "market.recipes",
    "products": "market.products",
    "stores": "market.stores",
}
DEFAULT_GROUPS: Sequence[str] = tuple(RESOURCE_TO_GROUP.values())
KEEPALIVE_EVENT = "market.keepalive"


def _resolve_groups(resource_param: Optional[str]) -> List[str]:
    if not resource_param:
        return list(DEFAULT_GROUPS)
    resource = resource_param.strip().lower()
    if resource not in RESOURCE_TO_GROUP:
        return list(DEFAULT_GROUPS)
    return [RESOURCE_TO_GROUP[resource]]


def _market_event_stream(*, groups: Sequence[str], user_id: int) -> Generator[bytes, None, None]:
    """Yield Server-Sent Events for given broker groups and user.
    This function is careful to never raise inside the generator to avoid 500s.
    """
    # Initial reconnection advice for the client (5s)
    yield f"retry: {5000}\n".encode("utf-8")
    # Initial keepalive so the UI shows 'connected'
    yield format_sse({}, event=KEEPALIVE_EVENT)

    broker = None
    subscription = None
    try:
        broker = get_event_broker()
        subscription = broker.subscribe(groups=list(groups), user_id=user_id)
        # Stream events
        for event in broker.iter_events(subscription):
            try:
                event_name = getattr(event, "group", None) or KEEPALIVE_EVENT
                payload = getattr(event, "payload", {}) or {}
                yield format_sse(payload, event=force_str(event_name))
            except Exception as exc:
                logger.warning("market events: failed to format event: %s", exc, exc_info=True)
    except Exception as exc:
        # If broker fails (e.g., not configured), downgrade to periodic keepalives
        logger.error("market events: broker unavailable: %s", exc, exc_info=True)
        while True:
            time.sleep(15)
            yield format_sse({}, event=KEEPALIVE_EVENT)
    finally:
        try:
            if broker and subscription is not None:
                broker.unsubscribe(subscription)
        except Exception:
            pass


class MarketEventStreamView(APIView):
    """SSE endpoint for marketplace realtime events.

    Usage (browser EventSource):
        GET /api/v1/market/events/?token=<JWT>&resource=recipes
    """
    permission_classes = [AllowAny]  # We'll authenticate manually using the ?token param

    def get(self, request: HttpRequest) -> HttpResponse:
        # 1) Authenticate from query/header
        token = extract_token_from_request(request)
        if not token:
            return Response({"detail": "Missing access token"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            user = authenticate_access_token(token)
        except Exception as exc:
            logger.info("market events: invalid token: %s", exc)
            return Response({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        # 2) Resolve target event groups
        groups = _resolve_groups(request.GET.get("resource"))

        # 3) Build streaming response
        stream = _market_event_stream(groups=groups, user_id=getattr(user, "id", 0))
        response = StreamingHttpResponse(stream, content_type="text/event-stream; charset=utf-8", status=200)
        # Hardening / buffering control for proxies
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Connection"] = "keep-alive"
        return response
