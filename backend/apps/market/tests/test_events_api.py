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
        for event in self._events:
            yield event


@pytest.mark.django_db
def test_market_events_requires_token(api_client):
    response = api_client.get(reverse("market:market-events"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_market_events_rejects_unknown_resource(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer", password="secret123")
    token = AccessToken.for_user(user)

    response = api_client.get(
        reverse("market:market-events"),
        {"resource": "invalid", "token": str(token)},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    payload = response.json()
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
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Cache-Control"] == "no-cache"
    assert response["Connection"] == "keep-alive"
    assert response["X-Accel-Buffering"] == "no"

    chunks = b"".join(response.streaming_content)
    body = chunks.decode("utf-8")

    assert ":ok\n\n" in body
    assert "event: market.keepalive" in body
    assert "event: market.recipes" in body
    assert "event: market.products" not in body
    assert "event: feed.news" not in body

    assert broker.unsubscribed == [broker.subscriber_id]
