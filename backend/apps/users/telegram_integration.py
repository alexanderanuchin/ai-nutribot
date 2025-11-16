import json
import logging
import os
import secrets
import time
from datetime import timedelta
from typing import Any, Dict, List
from urllib.parse import quote_plus

try:  # Optional dependency – degrade gracefully if missing
    import httpx
except Exception:  # pragma: no cover - optional dependency/setup
    httpx = None

try:  # Optional dependency – degrade to cache-based bridge if missing
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - optional dependency/setup
    redis = None

    class RedisError(Exception):
        pass

from django.conf import settings
from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

try:  # Optional logging helper
    from apps.common.logging import telegram_token_fingerprint
except Exception:  # pragma: no cover - optional dependency/setup
    telegram_token_fingerprint = None

from apps.users.models import Profile, TelegramIntegrationLink
from nutribot.middleware import get_request_id

logger = logging.getLogger("audit.telegram")

_REDIS_URL = os.getenv("REDIS_CACHE_URL") or os.getenv("REDIS_URL")
_EVENT_TTL = 3600
_EVENT_LIMIT = 50
_STREAM_TIMEOUT_SECONDS = 180
_STREAM_HEARTBEAT_INTERVAL = 5


def _redis_client() -> Any | None:
    if not _REDIS_URL or redis is None:
        return None
    try:
        return redis.from_url(_REDIS_URL, decode_responses=True)
    except Exception:  # pragma: no cover - optional dependency/setup
        return None


def _event_list_key(telegram_id: int) -> str:
    return f"telegram_bridge_events:{telegram_id}"


def _event_channel(telegram_id: int) -> str:
    return f"telegram_bridge:user:{telegram_id}"


class QueryStringJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            raw = request.query_params.get("token") or request.query_params.get("access_token")
            if raw:
                validated_token = self.get_validated_token(raw)
                return self.get_user(validated_token), validated_token
        return super().authenticate(request)


def _bot_username() -> str:
    return getattr(settings, "TELEGRAM_BOT_USERNAME", "CaloIQ_bot") or "CaloIQ_bot"


def _build_links(code: str) -> Dict[str, str]:
    username = _bot_username()
    encoded = quote_plus(code)
    return {
        "tg": f"tg://resolve?domain={username}&start={encoded}",
        "tme": f"https://t.me/{username}?start={encoded}",
        "startapp": f"https://t.me/{username}/app?startapp={encoded}",
    }


def _mask_token(token: str | None) -> str | None:
    if not token:
        return None
    if telegram_token_fingerprint:
        try:
            return telegram_token_fingerprint(token)
        except Exception:  # pragma: no cover - defensive
            pass
    if len(token) <= 8:
        return "***" + token[-2:]
    return f"{token[:4]}…{token[-4:]}"


def _send_telegram_message(telegram_id: int, text: str, rid: str) -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token or httpx is None:
        logger.warning(
            "telegram bridge missing_bot_token",
            extra={"rid": rid, "telegram_id": telegram_id},
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        response = httpx.post(url, json=payload, timeout=6.0)
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        ok = response.status_code == 200 and isinstance(data, dict) and data.get("ok") is True
        logger.info(
            "telegram bridge sent",
            extra={
                "rid": rid,
                "telegram_id": telegram_id,
                "status": response.status_code,
                "ok": ok,
                "token": _mask_token(token),
            },
        )
        return ok
    except Exception as exc:  # pragma: no cover - optional dependency/setup
        logger.warning(
            "telegram bridge send failed",
            extra={"rid": rid, "telegram_id": telegram_id, "error": str(exc)},
        )
        return False


def _cleanup_expired_links(user_id: int) -> None:
    now = timezone.now()
    expired = TelegramIntegrationLink.objects.filter(
        user_id=user_id,
        status=TelegramIntegrationLink.Status.PENDING,
        expires_at__lte=now,
    )
    if expired.exists():
        expired.update(status=TelegramIntegrationLink.Status.EXPIRED, updated_at=now)


def _get_or_create_link(user_id: int) -> TelegramIntegrationLink:
    _cleanup_expired_links(user_id)
    link = (
        TelegramIntegrationLink.objects.filter(
            user_id=user_id,
            status=TelegramIntegrationLink.Status.PENDING,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if link:
        return link
    expires_at = timezone.now() + timedelta(hours=24)
    code = secrets.token_urlsafe(12)
    return TelegramIntegrationLink.objects.create(
        user_id=user_id,
        code=code,
        expires_at=expires_at,
        payload={"reason": "deeplink"},
    )


def _rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=window_seconds)
        return False
    try:
        new_value = cache.incr(key)
    except Exception:  # pragma: no cover - cache backend differences
        new_value = (int(current) if isinstance(current, (int, float)) else 0) + 1
        cache.set(key, new_value, timeout=window_seconds)
    return int(new_value) > limit


class TelegramLinkStartView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        rid = getattr(request, "request_id", get_request_id())
        link = _get_or_create_link(request.user.id)
        links = _build_links(link.code)
        payload = {
            "code": link.code,
            "expires_at": link.expires_at,
            "links": links,
        }
        logger.info(
            "telegram integration link issued",
            extra={"rid": rid, "user_id": request.user.id, "code": link.code},
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class TelegramStatusView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rid = getattr(request, "request_id", get_request_id())
        profile, _ = Profile.objects.get_or_create(user=request.user)
        active_link = _get_or_create_link(request.user.id)
        links = _build_links(active_link.code)
        payload = {
            "linked": bool(profile.telegram_id or getattr(request.user, "telegram_id", None)),
            "telegram_id": profile.telegram_id or getattr(request.user, "telegram_id", None),
            "telegram_username": getattr(profile, "telegram_username", None)
            or getattr(request.user, "telegram_username", None),
            "app_username": getattr(request.user, "username", None),
            "linked_at": getattr(profile, "updated_at", None),
            "link": {
                "code": active_link.code,
                "expires_at": active_link.expires_at,
                "links": links,
            },
        }
        logger.info(
            "telegram integration status",
            extra={
                "rid": rid,
                "user_id": request.user.id,
                "linked": payload["linked"],
                "telegram_id": payload["telegram_id"],
            },
        )
        return Response(payload)


def _stream_events(telegram_id: int, rid: str):
    client = _redis_client()
    list_key = _event_list_key(telegram_id)
    channel = _event_channel(telegram_id)
    start = time.monotonic()
    cursor = 0

    if client is not None:
        try:
            backlog = client.lrange(list_key, -_EVENT_LIMIT, -1)
            for raw in backlog:
                yield f"data: {raw}\n\n"
                cursor += 1
        except RedisError as exc:
            logger.warning(
                "telegram bridge backlog failed",
                extra={"rid": rid, "telegram_id": telegram_id, "error": str(exc)},
            )

        pubsub = client.pubsub(ignore_subscribe_messages=True)
        try:
            pubsub.subscribe(channel)
            heartbeat = 0
            for message in pubsub.listen():
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if data:
                    yield f"data: {data}\n\n"
                    cursor += 1
                heartbeat += 1
                if heartbeat % _STREAM_HEARTBEAT_INTERVAL == 0:
                    yield "event: ping\ndata: {}\n\n"
                if time.monotonic() - start > _STREAM_TIMEOUT_SECONDS:
                    break
        finally:
            try:
                pubsub.close()
            except Exception:
                pass
    else:
        cache_key = list_key
        heartbeat = 0
        while True:
            events: List[Dict] = cache.get(cache_key, [])
            new_events = events[cursor:]
            for event in new_events:
                yield f"data: {json.dumps(event)}\n\n"
                cursor += 1
            heartbeat += 1
            if heartbeat % _STREAM_HEARTBEAT_INTERVAL == 0:
                yield "event: ping\ndata: {}\n\n"
            if time.monotonic() - start > _STREAM_TIMEOUT_SECONDS:
                break
            time.sleep(2)

    logger.info(
        "telegram bridge stream closed",
        extra={"rid": rid, "telegram_id": telegram_id, "cursor": cursor},
    )


def _append_event(telegram_id: int, event: Dict[str, str], *, rid: str) -> None:
    client = _redis_client()
    list_key = _event_list_key(telegram_id)
    channel = _event_channel(telegram_id)
    payload = json.dumps(event)
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.rpush(list_key, payload)
            pipe.ltrim(list_key, -_EVENT_LIMIT, -1)
            pipe.expire(list_key, _EVENT_TTL)
            pipe.publish(channel, payload)
            pipe.execute()
            return
        except RedisError as exc:
            logger.warning(
                "telegram bridge publish failed",
                extra={"rid": rid, "telegram_id": telegram_id, "error": str(exc)},
            )
    events: List[Dict] = cache.get(list_key, [])
    events.append(event)
    cache.set(list_key, events[-_EVENT_LIMIT:], timeout=_EVENT_TTL)


class TelegramBridgeSendView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        rid = getattr(request, "request_id", get_request_id())
        profile, _ = Profile.objects.get_or_create(user=request.user)
        telegram_id = profile.telegram_id or getattr(request.user, "telegram_id", None)
        if not telegram_id:
            logger.warning(
                "telegram bridge missing_telegram_id",
                extra={"rid": rid, "user_id": request.user.id},
            )
            return Response(
                {"detail": "Telegram is not linked"},
                status=status.HTTP_409_CONFLICT,
            )

        rl_key = f"telegram_bridge_rl:{telegram_id}"
        if _rate_limit(rl_key, limit=8, window_seconds=30):
            logger.warning(
                "telegram bridge rate_limited",
                extra={"rid": rid, "user_id": request.user.id, "telegram_id": telegram_id},
            )
            return Response(
                {"detail": "Too many bridge requests"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        text = (request.data or {}).get("text", "") if isinstance(request.data, dict) else ""
        client_id = (request.data or {}).get("client_id") if isinstance(request.data, dict) else None
        if not isinstance(text, str) or not text.strip():
            return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
        message = text.strip()[:4096]
        event = {
            "id": client_id if isinstance(client_id, str) and client_id else secrets.token_hex(8),
            "type": "user_message",
            "text": message,
            "ts": timezone.now().isoformat(),
        }
        _append_event(telegram_id, event, rid=rid)
        delivered = _send_telegram_message(telegram_id, message, rid)
        delivery_event = {
            "id": f"delivery-{event['id']}",
            "type": "status",
            "text": "Доставлено в бот" if delivered else "Не удалось доставить в бот",
            "ts": timezone.now().isoformat(),
        }
        _append_event(telegram_id, delivery_event, rid=rid)
        logger.info(
            "telegram bridge outbound enqueued",
            extra={
                "rid": rid,
                "user_id": request.user.id,
                "telegram_id": telegram_id,
                "length": len(message),
                "delivered": delivered,
            },
        )
        return Response({"accepted": True, "delivered": delivered})


class TelegramBridgeStreamView(APIView):
    authentication_classes = [QueryStringJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rid = getattr(request, "request_id", get_request_id())
        profile, _ = Profile.objects.get_or_create(user=request.user)
        telegram_id = profile.telegram_id or getattr(request.user, "telegram_id", None)
        if not telegram_id:
            logger.warning(
                "telegram bridge stream forbidden",
                extra={"rid": rid, "user_id": request.user.id},
            )
            return Response({"detail": "Telegram is not linked"}, status=status.HTTP_403_FORBIDDEN)
        logger.info(
            "telegram bridge stream start",
            extra={"rid": rid, "user_id": request.user.id, "telegram_id": telegram_id},
        )
        response = StreamingHttpResponse(
            _stream_events(telegram_id, rid),
            status=status.HTTP_200_OK,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

