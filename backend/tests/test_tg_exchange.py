import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest
from django.contrib.auth import get_user_model

from apps.users.models import TelegramSession


def build_init_data(bot_token: str, payload: dict) -> str:
    data = payload.copy()
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)


@pytest.mark.django_db
def test_tg_exchange_returns_tokens_and_profile_summary(client, settings):
    settings.TELEGRAM_BOT_TOKEN = "bot-token"
    user_payload = {"id": 12345, "first_name": "Иван", "last_name": "Петров"}
    raw_payload = {
        "auth_date": "1700000000",
        "query_id": "AAEAAQ",
        "user": json.dumps(user_payload, separators=(",", ":"), ensure_ascii=False),
    }
    init_data = build_init_data(settings.TELEGRAM_BOT_TOKEN, raw_payload)

    response = client.post("/api/users/auth/tg_exchange/", {"init_data": init_data})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["first_name"] == "Иван"
    assert payload["user"]["phone"] == "tg_12345"
    assert payload["profile"]["telegram_id"] == 12345
    assert payload["wallet"] == {"stars": "0", "calo": "0.00"}
    assert "metrics" in payload

    User = get_user_model()
    user = User.objects.get(username="tg_12345")
    profile = user.profile
    assert profile.telegram_id == 12345
    assert user.first_name == "Иван"
    assert user.last_name == "Петров"

    session = TelegramSession.objects.get(profile=profile)
    assert session.access_token
    assert session.refresh_token


@pytest.mark.django_db
def test_tg_exchange_reuses_existing_profile(client, settings):
    settings.TELEGRAM_BOT_TOKEN = "bot-token"
    User = get_user_model()
    existing = User.objects.create_user(username="existing", password="StrongPass!1")
    profile = existing.profile
    profile.telegram_id = 777
    profile.save(update_fields=["telegram_id"])

    raw_payload = {
        "auth_date": "1700000000",
        "user": json.dumps({"id": 777, "first_name": "Alex"}),
    }
    init_data = build_init_data(settings.TELEGRAM_BOT_TOKEN, raw_payload)

    response = client.post("/api/users/auth/tg_exchange/", {"init_data": init_data})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["phone"] == "existing"

    existing.refresh_from_db()
    assert existing.profile.telegram_id == 777
    assert User.objects.filter(username="existing").count() == 1
    assert not User.objects.filter(username="tg_777").exists()

    session = TelegramSession.objects.get(profile=existing.profile)
    assert session.access_token
    assert session.refresh_token


@pytest.mark.django_db
def test_tg_exchange_rejects_invalid_signature(client, settings):
    settings.TELEGRAM_BOT_TOKEN = "bot-token"
    payload = {
        "auth_date": "1700000000",
        "user": json.dumps({"id": 321}),
        "hash": "deadbeef",
    }
    init_data = urlencode(payload)

    response = client.post("/api/users/auth/tg_exchange/", {"init_data": init_data})

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"]