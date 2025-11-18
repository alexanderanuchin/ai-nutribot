import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Profile, TelegramSession


@pytest.mark.django_db
def test_telegram_session_requires_bot_key(client, settings):
    settings.TELEGRAM_BOT_KEY = "secret"
    response = client.get("/api/users/bot/telegram/session/123/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_telegram_session_returns_tokens(client, settings):
    settings.TELEGRAM_BOT_KEY = "secret"
    user = get_user_model().objects.create_user(username="tg-user")
    profile = user.profile
    profile.telegram_id = 123
    profile.save(update_fields=["telegram_id"])
    refresh = RefreshToken.for_user(user)
    session = TelegramSession.objects.create(
        profile=profile,
        access_token=str(refresh.access_token),
        refresh_token=str(refresh),
        expires_at=timezone.now() + timedelta(hours=1),
    )

    response = client.get(
        "/api/users/bot/telegram/session/123/",
        HTTP_X_BOT_KEY=settings.TELEGRAM_BOT_KEY,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access"] == session.access_token
    assert payload["refresh"] == session.refresh_token
    assert payload["expires_at"] == session.expires_at.isoformat()


@pytest.mark.django_db
def test_telegram_session_refreshes_expired_access_token(client, settings):
    settings.TELEGRAM_BOT_KEY = "secret"
    user = get_user_model().objects.create_user(username="tg-user-expired")
    profile = user.profile
    profile.telegram_id = 321
    profile.save(update_fields=["telegram_id"])
    refresh = RefreshToken.for_user(user)
    expired_access = refresh.access_token
    expired_access.set_exp(from_time=timezone.now() - timedelta(hours=2), lifetime=timedelta(hours=1))
    session = TelegramSession.objects.create(
        profile=profile,
        access_token=str(expired_access),
        refresh_token=str(refresh),
        expires_at=timezone.now() - timedelta(hours=1),
    )

    response = client.get(
        "/api/users/bot/telegram/session/321/",
        HTTP_X_BOT_KEY=settings.TELEGRAM_BOT_KEY,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["refresh"] == session.refresh_token
    assert payload["access"] != session.access_token

    session.refresh_from_db()
    assert session.access_token == payload["access"]
    assert session.expires_at > timezone.now()
