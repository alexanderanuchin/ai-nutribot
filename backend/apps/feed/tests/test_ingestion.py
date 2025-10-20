from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest
import responses
import requests

from apps.feed import ingestion as ingestion_module
from apps.feed.ingestion import FeedItemPayload, FeedSourceConfig, ingest_sources
from apps.feed.models import NewsArticle


def test_normalise_payload_union_categories(settings):
    settings.BOT_INTERNAL_KEY = "integration-key"
    config = FeedSourceConfig(
        name="health-news",
        url="https://news.example/api",
        categories=["fitness"],
    )
    payload = FeedItemPayload(
        id="abc123",
        title=" Health benefits of avocado ",
        summary=" Rich in nutrients ",
        link="https://publisher.example/avocado",
        published_at=datetime(2024, 7, 1, 12, 30, tzinfo=dt_timezone.utc),
        source="Daily Health",
        categories=["wellness"],
        tonality="positive",
        preview_image_url="https://publisher.example/avocado.jpg",
        toxicity_score=0.1356,
        clickbait_score=0.2049,
    )

    defaults = ingestion_module._normalise_payload(payload, source=config, rid="rid-1")

    assert defaults["title"] == "Health benefits of avocado"
    assert defaults["lead"] == "Rich in nutrients"
    assert defaults["source_name"] == "Daily Health"
    assert defaults["source_categories"] == ["fitness", "wellness"]
    assert str(defaults["preview_image_url"]) == "https://publisher.example/avocado.jpg"
    assert defaults["tonality"] == NewsArticle.Tonality.POSITIVE
    assert defaults["toxicity_score"] == Decimal("0.1356")
    assert defaults["ingestion_metadata"]["external_id"] == "abc123"
    assert defaults["ingestion_source"] == "health-news"


@pytest.mark.django_db
def test_ingest_sources_creates_article(settings):
    settings.BOT_INTERNAL_KEY = "shared-secret"
    settings.FEED_INGESTION_SOURCES = [
        {
            "name": "health-news",
            "url": "https://news.example/api",
            "categories": ["fitness"],
            "timeout": 2,
        }
    ]
    payload = {
        "external_id": "story-1",
        "title": "Morning workout lowers stress",
        "description": "Researchers confirm reduced cortisol levels",
        "url": "https://publisher.example/workout",
        "publishedAt": "2024-07-01T07:00:00Z",
        "sourceName": "Wellness Wire",
        "categories": ["wellness"],
        "sentiment": "neutral",
        "imageUrl": "https://publisher.example/workout.jpg",
    }

    class _ResponsesHttpxResponse:
        def __init__(self, response: requests.Response) -> None:
            self._response = response

        def json(self) -> dict:
            return self._response.json()

        def raise_for_status(self) -> None:
            self._response.raise_for_status()

    class _ResponsesHttpxClient:
        def get(self, url: str, *, headers=None, params=None, timeout=None):
            response = requests.request("GET", url, headers=headers, params=params, timeout=timeout)
            return _ResponsesHttpxResponse(response)

        def close(self) -> None:  # pragma: no cover - compatibility shim
            return None

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url="https://news.example/api",
            json={"items": [payload]},
            status=200,
            match=[
                responses.matchers.header_matcher({"X-Integration-Key": "shared-secret"}),
                responses.matchers.query_param_matcher({"categories": "fitness"}),
            ],
        )

        client = _ResponsesHttpxClient()
        result = ingest_sources(rid="test-rid", http_client=client)

    assert result["processed"] == 1
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["failed_sources"] == []

    article = NewsArticle.objects.get(source_id="health-news:story-1")
    assert article.title == "Morning workout lowers stress"
    assert article.lead == "Researchers confirm reduced cortisol levels"
    assert article.source_name == "Wellness Wire"
    assert article.ingestion_rid == "test-rid"
    assert article.source_categories == ["fitness", "wellness"]
    assert article.ingestion_metadata["payload_categories"] == ["wellness"]