from __future__ import annotations

import types

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse

from apps.feed import admin as feed_admin  # noqa: F401  # ensure admin registration
from apps.feed.apps import FeedConfig
from apps.feed.models import NewsArticle


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def ensure_feed_groups(db):
    FeedConfig._ensure_default_groups()


@pytest.fixture
def moderator_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="moderator",
        email="moderator@example.com",
        password="password",
        is_staff=True,
    )
    group = Group.objects.get(name="Feed moderators")
    user.groups.add(group)
    return user


@pytest.fixture
def editor_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="editor",
        email="editor@example.com",
        password="password",
        is_staff=True,
    )
    group = Group.objects.get(name="Feed editors")
    user.groups.add(group)
    return user


@pytest.fixture
def rf():
    return RequestFactory()


def _attach_messages(request):
    setattr(request, "session", {})
    setattr(request, "_messages", FallbackStorage(request))


def test_admin_changelist_and_changeform_access(client, editor_user):
    article = NewsArticle.objects.create(
        source_id="src-1",
        title="Hello world",
        lead="Lead",
        body="Body",
        source_name="Source",
        source_url="https://example.com",
    )
    client.force_login(editor_user)
    changelist_url = reverse("admin:feed_newsarticle_changelist")
    changeform_url = reverse("admin:feed_newsarticle_change", args=[article.pk])

    response = client.get(changelist_url)
    assert response.status_code == 200

    response = client.get(changeform_url)
    assert response.status_code == 200


def test_publish_and_unpublish_actions(rf, moderator_user):
    article = NewsArticle.objects.create(
        source_id="src-2",
        title="Draft",
        lead="Lead",
        source_name="Source",
        source_url="https://example.com/2",
        is_published=False,
    )
    request = rf.post("/admin/feed/newsarticle/")
    request.user = moderator_user
    _attach_messages(request)
    model_admin = admin.site._registry[NewsArticle]

    model_admin.mark_as_published(request, NewsArticle.objects.filter(pk=article.pk))
    article.refresh_from_db()
    assert article.is_published is True

    model_admin.mark_as_unpublished(request, NewsArticle.objects.filter(pk=article.pk))
    article.refresh_from_db()
    assert article.is_published is False


def test_translate_action_updates_fields(rf, settings, moderator_user, monkeypatch):
    settings.FEED_TRANSLATE_RU_ENABLED = True
    article = NewsArticle.objects.create(
        source_id="src-3",
        title="Original",
        lead="Lead",
        source_name="Source",
        source_url="https://example.com/3",
        lang="en",
        translated=False,
    )

    class DummyService:
        def __init__(self) -> None:
            self.is_available = True
            self.provider = types.SimpleNamespace(name="dummy")

    def fake_service():
        return DummyService()

    def fake_normalize(payload, *, rid=None, translation_service=None):
        return {
            "title": "Перевод",
            "lead": "Лид",
            "body": "Текст",
            "title_orig": payload.get("title"),
            "lead_orig": payload.get("lead"),
            "body_orig": payload.get("body"),
            "lang": "ru",
            "translated": True,
            "translation_provider": "dummy",
        }

    monkeypatch.setattr("apps.feed.admin.get_translation_service", fake_service)
    monkeypatch.setattr("apps.feed.admin.normalize_and_translate_article", fake_normalize)

    request = rf.post("/admin/feed/newsarticle/translate")
    request.user = moderator_user
    _attach_messages(request)
    model_admin = admin.site._registry[NewsArticle]

    model_admin.translate_to_russian(request, NewsArticle.objects.filter(pk=article.pk))
    article.refresh_from_db()

    assert article.title == "Перевод"
    assert article.lead == "Лид"
    assert article.translated is True
    assert article.translation_provider == "dummy"


def test_admin_search_filters(client, moderator_user):
    NewsArticle.objects.bulk_create(
        [
            NewsArticle(
                source_id="s1",
                title="Protein helps recovery",
                lead="Lead",
                source_name="Source",
                source_url="https://example.com/a",
            ),
            NewsArticle(
                source_id="s2",
                title="Овощи и витамины",
                lead="Описание",
                source_name="Другой",
                source_url="https://example.com/b",
                is_published=False,
            ),
        ]
    )
    client.force_login(moderator_user)
    changelist_url = reverse("admin:feed_newsarticle_changelist")

    response = client.get(changelist_url, {"q": "protein"})
    assert response.status_code == 200
    queryset = response.context_data["cl"].queryset
    assert queryset.count() == 1
    assert queryset.first().source_id == "s1"

    response = client.get(changelist_url, {"is_published__exact": "0"})
    queryset = response.context_data["cl"].queryset
    assert queryset.count() == 1
    assert queryset.first().source_id == "s2"