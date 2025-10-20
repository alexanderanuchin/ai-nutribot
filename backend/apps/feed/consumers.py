from __future__ import annotations

from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.exceptions import AuthenticationFailed

from .authentication import authenticate_access_token

GROUP_MAP = {
    "news": "feed.news",
    "feed.news": "feed.news",
    "recipes": "feed.recipes",
    "feed.recipes": "feed.recipes",
    "deals": "feed.deals",
    "feed.deals": "feed.deals",
}

VALID_GROUPS = set(GROUP_MAP.values())


class FeedConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        query_params = parse_qs(self.scope.get("query_string", b"").decode())
        token = query_params.get("token", [None])[0]
        if not token:
            await self.close(code=4401)
            return
        try:
            user = await sync_to_async(authenticate_access_token)(token)
        except AuthenticationFailed:
            await self.close(code=4401)
            return
        self.scope["user"] = user
        feed_type = query_params.get("type", ["news"])[0] or "news"
        if feed_type == "all":
            self.group_names = sorted(VALID_GROUPS)
        else:
            group_name = GROUP_MAP.get(feed_type)
            if group_name is None and feed_type in VALID_GROUPS:
                group_name = feed_type
            if group_name is None:
                group_name = "feed.news"
            self.group_names = [group_name]
        for group in self.group_names:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "group": feed_type, "groups": self.group_names})

    async def disconnect(self, close_code):  # pragma: no cover - network lifecycle
        for group in getattr(self, "group_names", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):  # pragma: no cover - currently fire-and-forget
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def feed_event(self, event):
        payload = event.get("event")
        if payload is None:
            return
        await self.send_json({"type": "event", "payload": payload, "group": event.get("group")})
