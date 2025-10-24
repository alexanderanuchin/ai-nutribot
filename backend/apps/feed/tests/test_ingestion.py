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
from apps.feed.services.ingest_pipeline import normalize_and_translate_article
from apps.feed.services.translation import TranslationOutcome


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
    assert defaults["body"] is None
    assert defaults["source_name"] == "Daily Health"
    assert defaults["source_categories"] == ["fitness", "wellness"]
    assert str(defaults["preview_image_url"]) == "https://publisher.example/avocado.jpg"
    assert defaults["tonality"] == NewsArticle.Tonality.POSITIVE
    assert defaults["toxicity_score"] == Decimal("0.1356")
    assert defaults["ingestion_metadata"]["external_id"] == "abc123"
    assert defaults["ingestion_source"] == "health-news"
    assert defaults["lang"] in {"en", "und"}
    assert defaults["translated"] is False
    assert defaults["translation_provider"] == ""
    assert defaults["title_orig"] is None


def test_normalize_and_translate_article_translates(monkeypatch, settings):
    settings.FEED_TRANSLATE_RU_ENABLED = True
    settings.TRANSLATE_TARGET_LANG = "ru"

    class StubTranslationService:
        def __init__(self):
            self.providers = ["stub"]

        def translate_texts(self, texts, *, source_lang, target_lang, rid=None):
            return TranslationOutcome(
                texts=[f"RU:{text}" if text else text for text in texts],
                provider="stub",
                source_lang=source_lang,
            )

    stub_service = StubTranslationService()
    monkeypatch.setattr(
        "apps.feed.services.ingest_pipeline.get_translation_service",
        lambda: stub_service,
    )
    monkeypatch.setattr(
        "apps.feed.services.ingest_pipeline.detect_language",
        lambda parts: "en",
    )

    result = normalize_and_translate_article(
        {"title": "Hello", "lead": "World", "body": "Body text"},
        rid="rid-translate",
    )

    assert result["title"] == "RU:Hello"
    assert result["lead"] == "RU:World"
    assert result["body"] == "RU:Body text"
    assert result["title_orig"] == "Hello"
    assert result["lead_orig"] == "World"
    assert result["body_orig"] == "Body text"
    assert result["lang"] == "en"
    assert result["translated"] is True
    assert result["translation_provider"] == "stub"


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
    assert article.body is None
    assert article.source_name == "Wellness Wire"
    assert article.ingestion_rid == "test-rid"
    assert article.source_categories == ["fitness", "wellness"]
    assert article.ingestion_metadata["payload_categories"] == ["wellness"]
    assert article.lang in {"en", "und"}
    assert article.translated is False
    assert article.translation_provider == ""


@pytest.mark.django_db
def test_ingest_sources_honours_limit_per_source(settings):
    settings.FEED_INGESTION_SOURCES = [
        {
            "name": "limited-feed",
            "url": "https://news.example/api",
            "timeout": 2,
        }
    ]

    items = [
        {
            "external_id": f"story-{index}",
            "title": f"Story {index}",
            "description": "Summary",
            "url": f"https://publisher.example/story-{index}",
            "publishedAt": f"2024-07-{index:02d}T0{index%10}:00:00Z",
            "sourceName": "Limited Feed",
            "categories": [],
            "sentiment": "neutral",
            "imageUrl": None,
        }
        for index in range(1, 9)
    ]

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url="https://news.example/api",
            json={"items": items},
            status=200,
        )

        client = _ResponsesHttpxClient()
        result = ingest_sources(
            rid="limit-rid",
            http_client=client,
            items_limit_per_source=5,
        )

    assert result["processed"] == 5
    assert NewsArticle.objects.count() == 5
    stored_ids = set(
        NewsArticle.objects.values_list("source_id", flat=True)
    )
    assert stored_ids == {
        "limited-feed:story-8",
        "limited-feed:story-7",
        "limited-feed:story-6",
        "limited-feed:story-5",
        "limited-feed:story-4",
    }


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