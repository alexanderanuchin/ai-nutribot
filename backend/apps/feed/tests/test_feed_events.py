from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.feed.events import publish_news_article_event
from apps.feed.models import FeedTag, NewsArticle


@pytest.mark.django_db
def test_publish_news_article_event_includes_moderation(monkeypatch):
    tag = FeedTag.objects.create(name='Science', slug='science', kind=FeedTag.Kind.NEWS)
    article = NewsArticle.objects.create(
        source_id='ext-news',
        title='Новое исследование питания',
        lead='Лёгкий пересказ исследования',
        source_name='NutriNews',
        source_url='https://example.com/news',
        published_at=timezone.now(),
        toxicity_score=Decimal('0.1200'),
        clickbait_score=Decimal('0.1800'),
        is_flagged=False,
    )
    article.tags.add(tag)

    captured = {}

    def _capture_event(event):
        captured['event'] = event

    monkeypatch.setattr('apps.feed.events.publish_feed_event', _capture_event)

    publish_news_article_event(article, action='created', rid='rid-test')

    event = captured['event']
    assert event.group_name == 'feed.news'
    payload = event.payload
    assert payload['action'] == 'created'
    assert payload['meta']['rid'] == 'rid-test'
    assert payload['meta']['article_id'] == article.id
    assert payload['article']['source_id'] == 'ext-news'
    assert payload['article']['toxicity_score'] == '0.1200'
    assert payload['article']['clickbait_score'] == '0.1800'
    assert payload['article']['tags'][0]['slug'] == 'science'


@pytest.mark.django_db
def test_moderation_signal_emits_event(monkeypatch):
    events: list[tuple[str, bool]] = []

    def _capture(article: NewsArticle, action: str, *, rid=None):
        events.append((action, article.is_flagged))

    monkeypatch.setattr('apps.feed.signals.publish_news_article_event', _capture)

    article = NewsArticle.objects.create(
        source_id='ext-moderation',
        title='Новость на модерации',
        lead='Лид новости',
        source_name='Nutri',
        source_url='https://example.com/moderation',
        published_at=timezone.now(),
        is_flagged=False,
    )

    article.is_flagged = True
    article.save(update_fields=['is_flagged'])

    assert events == [('moderated', True)]