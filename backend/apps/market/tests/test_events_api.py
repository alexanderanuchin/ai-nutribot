import json
from collections.abc import Iterable

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.feed.events import FeedEvent


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


class DummyBroker:
    def __init__(self, events: Iterable[FeedEvent]):
        self._events = list(events)
        self.subscriber_id = "dummy-subscriber"
        self.unsubscribed: list[str] = []

    def subscribe(self) -> tuple[str, object]:
        return self.subscriber_id, object()

    def unsubscribe(self, subscriber_id: str) -> None:
        self.unsubscribed.append(subscriber_id)

    def iter_events(self, _queue: object):
        yield from self._events


@pytest.mark.django_db
def test_market_events_requires_token(api_client):
    response = api_client.get(
        reverse("market:market-events"),
        HTTP_ACCEPT="text/event-stream",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_market_events_rejects_invalid_token(api_client):
    response = api_client.get(
        reverse("market:market-events"),
        {"token": "invalid"},
        HTTP_ACCEPT="text/event-stream",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_market_events_rejects_unknown_resource(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer", password="secret123")
    token = AccessToken.for_user(user)

    response = api_client.get(
        reverse("market:market-events"),
        {"resource": "invalid", "token": str(token)},
        HTTP_ACCEPT="text/event-stream",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    payload = json.loads(response.content.decode("utf-8"))
    assert payload["resource"] == "Unsupported resource"


@pytest.mark.django_db
def test_market_events_stream_filters_groups(monkeypatch, api_client, django_user_model):
    user = django_user_model.objects.create_user(username="streamer", password="secret123")
    token = AccessToken.for_user(user)

    events = [
        FeedEvent(group_name="feed.keepalive", payload={"ping": 1}),
        FeedEvent(group_name="market.recipes", payload={"fresh_count": 2}),
        FeedEvent(group_name="market.products", payload={"fresh_count": 4}),
        FeedEvent(group_name="feed.news", payload={"id": 7}),
    ]
    broker = DummyBroker(events)
    monkeypatch.setattr("apps.market.api.events.get_event_broker", lambda: broker)

    response = api_client.get(
        reverse("market:market-events"),
        {"resource": "recipes", "token": str(token)},
        HTTP_ACCEPT="text/event-stream",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Cache-Control"] == "no-cache"
    assert response["X-Accel-Buffering"] == "no"
    assert "Connection" not in response

    chunks = b"".join(response.streaming_content)
    body = chunks.decode("utf-8")

    assert ":ok\n\n" in body
    assert "event: market.keepalive" in body
    assert "event: market.recipes" in body
    assert "event: market.products" not in body
    assert "event: feed.news" not in body

    assert broker.unsubscribed == [broker.subscriber_id]


@pytest.mark.django_db
def test_market_events_handles_byte_formatter(monkeypatch, api_client, django_user_model):
    user = django_user_model.objects.create_user(username="streamer2", password="secret123")
    token = AccessToken.for_user(user)

    events = [
        FeedEvent(group_name="market.recipes", payload={"fresh_count": 2}),
    ]
    broker = DummyBroker(events)
    monkeypatch.setattr("apps.market.api.events.get_event_broker", lambda: broker)

    def byte_formatter(event: FeedEvent) -> bytes:
        payload = json.dumps(event.payload, ensure_ascii=False).encode("utf-8")
        return (
            b"event: "
            + event.group_name.encode("utf-8")
            + b"\n"
            + b"data: "
            + payload
            + b"\n\n"
        )

    monkeypatch.setattr("apps.market.api.events.format_sse", byte_formatter)

    response = api_client.get(
        reverse("market:market-events"),
        {"resource": "recipes", "token": str(token)},
        HTTP_ACCEPT="text/event-stream",
    )

    assert response.status_code == status.HTTP_200_OK
    chunks = list(response.streaming_content)
    assert all(isinstance(chunk, bytes) for chunk in chunks)
    body = b"".join(chunks).decode("utf-8")
    assert "event: market.keepalive" in body
    assert "event: market.recipes" in body


@pytest.mark.django_db
def test_market_events_fallbacks_on_invalid_chunks(monkeypatch, api_client, django_user_model):
    user = django_user_model.objects.create_user(username="streamer3", password="secret123")
    token = AccessToken.for_user(user)

    events = [
        FeedEvent(group_name="market.recipes", payload={"fresh_count": 3}),
    ]
    broker = DummyBroker(events)
    monkeypatch.setattr("apps.market.api.events.get_event_broker", lambda: broker)

    def invalid_formatter(event: FeedEvent):
        return [b"event: broken\n", 255]

    monkeypatch.setattr("apps.market.api.events.format_sse", invalid_formatter)

    response = api_client.get(
        reverse("market:market-events"),
        {"resource": "recipes", "token": str(token)},
        HTTP_ACCEPT="text/event-stream",
    )

    assert response.status_code == status.HTTP_200_OK
    chunks = list(response.streaming_content)
    assert all(isinstance(chunk, bytes) for chunk in chunks)
    body = b"".join(chunks).decode("utf-8")
    assert "event: market.recipes" in body
    assert "data: {\"fresh_count\": 3}" in body
