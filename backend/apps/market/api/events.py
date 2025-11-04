from __future__ import annotations

import logging
from typing import Iterable

from django.http import StreamingHttpResponse
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.views import APIView

from apps.feed.authentication import authenticate_access_token, extract_token_from_request
from apps.feed.events import FeedEvent, format_sse, get_event_broker
from apps.common.renderers import EventStreamRenderer
from nutribot.middleware import get_request_id

logger = logging.getLogger("market.api.events")

RESOURCE_TO_GROUP = {
    "recipes": "market.recipes",
    "products": "market.products",
    "stores": "market.stores",
}


class MarketEventStreamView(APIView):
    """Proxy SSE endpoint exposing marketplace events."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list[type] = []
    renderer_classes = [EventStreamRenderer]

    def get(self, request, *args, **kwargs):
        token = extract_token_from_request(request)
        if not token:
            raise AuthenticationFailed("Authentication credentials were not provided.")
        user = authenticate_access_token(token)
        request.user = user

        resource = request.query_params.get("resource")
        if resource:
            if resource not in RESOURCE_TO_GROUP:
                raise ValidationError({"resource": "Unsupported resource"})
            group_filter = RESOURCE_TO_GROUP[resource]
        else:
            group_filter = None

        broker = get_event_broker()
        subscriber_id, queue = broker.subscribe()
        rid = getattr(request, "request_id", get_request_id())

        logger.info(
            "market events stream subscribed",
            extra={
                "rid": rid,
                "user_id": user.id,
                "subscriber_id": subscriber_id,
                "resource": resource or "*",
            },
        )

        def event_stream() -> Iterable[bytes]:
            try:
                yield b":ok\n\n"
                for event in broker.iter_events(queue):
                    group_name = event.group_name
                    if group_name == "feed.keepalive":
                        keepalive = FeedEvent(group_name="market.keepalive", payload=event.payload)
                        yield from format_sse(keepalive)
                        continue
                    if not group_name.startswith("market."):
                        continue
                    if group_filter and group_name != group_filter:
                        continue
                    yield from format_sse(event)
            finally:
                broker.unsubscribe(subscriber_id)
                logger.debug(
                    "market events stream disconnected",
                    extra={
                        "rid": rid,
                        "user_id": user.id,
                        "subscriber_id": subscriber_id,
                        "resource": resource or "*",
                    },
                )

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["X-Accel-Buffering"] = "no"
        return response
