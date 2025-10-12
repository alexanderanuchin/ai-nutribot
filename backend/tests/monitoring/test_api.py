import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.monitoring.models import ApplicationLog


@pytest.fixture()
def auth_client(db):
    user = get_user_model().objects.create_user(
        username="user@example.com",
        password="StrongPass!1",
        first_name="Test",
        last_name="User",
    )
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, user


@pytest.mark.django_db
def test_bot_can_push_application_log(settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    client = APIClient()
    payload = {
        "level": "info",
        "logger": "bot.webapp",
        "message": "update received",
        "request_id": "RID-4242",
        "extra": {"update_id": 123},
    }

    response = client.post(
        "/api/monitoring/application/logs/",
        payload,
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
    )

    assert response.status_code == 201
    entry = ApplicationLog.objects.get()
    assert entry.level == ApplicationLog.Level.INFO
    assert entry.logger_name == "bot.webapp"
    assert entry.request_id == "RID-4242"
    assert entry.extra["component"] == "bot"
    assert entry.extra["update_id"] == 123


@pytest.mark.django_db
def test_authenticated_user_can_push_application_log(auth_client):
    client, _ = auth_client
    payload = {
        "level": "INFO",
        "message": "webapp topup initiated",
        "request_id": "RID-123",
        "extra": {"amount": 150},
    }

    response = client.post("/api/monitoring/application/logs/", payload, format="json")

    assert response.status_code == 201
    entry = ApplicationLog.objects.get()
    assert entry.logger_name == "webapp.monitoring"
    assert entry.request_id == "RID-123"
    assert entry.extra["component"] == "webapp"
    assert entry.extra["amount"] == 150


@pytest.mark.django_db
def test_bulk_entries_are_supported(settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    client = APIClient()
    payload = {
        "entries": [
            {"level": "DEBUG", "message": "first", "request_id": "RID-1"},
            {"level": "WARNING", "message": "second", "request_id": "RID-1"},
        ]
    }

    response = client.post(
        "/api/monitoring/application/logs/",
        payload,
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
    )

    assert response.status_code == 201
    assert ApplicationLog.objects.count() == 2
    levels = list(ApplicationLog.objects.order_by("pk").values_list("level", flat=True))
    assert levels == [ApplicationLog.Level.DEBUG, ApplicationLog.Level.WARNING]


@pytest.mark.django_db
def test_requires_authentication():
    client = APIClient()
    response = client.post(
        "/api/monitoring/application/logs/",
        {"level": "INFO", "message": "nope"},
        format="json",
    )

    assert response.status_code == 401
    assert ApplicationLog.objects.count() == 0