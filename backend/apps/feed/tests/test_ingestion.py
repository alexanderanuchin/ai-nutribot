from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import httpx
import pytest
import responses
import requests

from apps.feed import ingestion as ingestion_module
from apps.feed.ingestion import FeedItemPayload, FeedSourceConfig, ingest_sources
from apps.feed.models import NewsArticle


class _ResponsesHttpxResponse:
    def __init__(self, response: requests.Response) -> None:
        self._response = response

    @property
    def headers(self):
        return self._response.headers

    @property
    def text(self) -> str:
        return self._response.text

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


@pytest.mark.django_db
def test_ingest_sources_notifies_on_failed_sources(monkeypatch, settings):
    settings.FEED_INGESTION_SOURCES = [
        {
            "name": "health-news",
            "url": "https://news.example/api",
            "timeout": 1,
        }
    ]

    metrics_calls: list[dict] = []
    notify_calls: list[dict] = []

    def _fake_record_metrics(*, result, duration_seconds):
        metrics_calls.append({"result": result, "duration": duration_seconds})

    def _fake_notify(**kwargs):
        notify_calls.append(kwargs)

    monkeypatch.setattr(ingestion_module, "record_ingestion_metrics", _fake_record_metrics)
    monkeypatch.setattr(ingestion_module, "notify_ingestion_failure", _fake_notify)

    class _FailingHttpxClient:
        def get(self, *args, **kwargs):
            raise httpx.HTTPError("boom")

        def close(self):  # pragma: no cover - compatibility shim
            return None

    result = ingest_sources(rid="rid-1", http_client=_FailingHttpxClient())

    assert result["failed_sources"] == ["health-news"]
    assert metrics_calls and metrics_calls[0]["result"]["rid"] == "rid-1"
    assert notify_calls and notify_calls[0]["failed_sources"] == ["health-news"]
    assert notify_calls[0]["rid"] == "rid-1"


@pytest.mark.django_db
def test_ingest_sources_parses_rss_feed(settings):
    settings.FEED_INGESTION_SOURCES = [
        {
            "name": "rss-feed",
            "url": "https://news.example/rss",
            "categories": ["nutrition"],
            "timeout": 2,
        }
    ]

    rss_payload = """<?xml version='1.0' encoding='UTF-8'?>
        <rss version="2.0">
          <channel>
            <title>Nutrition Insights</title>
            <item>
              <title>Daily fruit intake reduces risk</title>
              <link>https://publisher.example/articles/fruit-intake</link>
              <guid isPermaLink="false">fruit-intake-001</guid>
              <description>Comprehensive study covering 10k participants.</description>
              <pubDate>Mon, 01 Jul 2024 09:00:00 GMT</pubDate>
              <category>health</category>
              <category>nutrition</category>
            </item>
          </channel>
        </rss>
        """

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url="https://news.example/rss",
            body=rss_payload,
            status=200,
            content_type="application/rss+xml",
        )

        client = _ResponsesHttpxClient()
        result = ingest_sources(rid="rss-rid", http_client=client)

    assert result["processed"] == 1
    assert result["created"] == 1

    article = NewsArticle.objects.get(source_id="rss-feed:fruit-intake-001")
    assert article.title == "Daily fruit intake reduces risk"
    assert article.lead.startswith("Comprehensive study")
    assert article.source_name == "Nutrition Insights"
    assert set(article.source_categories) == {"health", "nutrition"}


@pytest.mark.django_db
def test_ingest_sources_uses_json_blueprint(settings):
    settings.FEED_INGESTION_SOURCES = [
        {
            "name": "who-stream",
            "url": "https://news.example/who",
            "categories": ["global"],
            "parser": {"blueprint": "who-news"},
        }
    ]

    payload = {
        "value": [
            {
                "id": 101,
                "title": "WHO issues new nutrition guidance",
                "summary": "Comprehensive policy update",
                "slug": "news-room/articles/new-guidance",
                "date": "2024-07-02T12:00:00Z",
                "topics": [{"title": "Nutrition"}],
                "image": {"url": "https://cdn.who.int/media/guidance.jpg"},
            }
        ]
    }

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url="https://news.example/who",
            json=payload,
            status=200,
        )

        client = _ResponsesHttpxClient()
        result = ingest_sources(rid="who-rid", http_client=client)

    assert result["processed"] == 1
    assert result["created"] == 1

    article = NewsArticle.objects.get(source_id="who-stream:101")
    assert article.title == "WHO issues new nutrition guidance"
    assert article.source_name == "WHO"
    assert article.source_categories == ["global", "nutrition"]
    assert article.preview_image_url == "https://cdn.who.int/media/guidance.jpg"