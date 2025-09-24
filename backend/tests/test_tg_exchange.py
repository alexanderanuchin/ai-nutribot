import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest
from django.contrib.auth import get_user_model


def build_init_data(bot_token: str, payload: dict) -> str:
    data = payload.copy()
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    data["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)


@pytest.mark.django_db
def test_tg_exchange_returns_tokens_and_binds_profile(client, settings):
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
    tokens = response.json()
    assert tokens["access"]
    assert tokens["refresh"]

    User = get_user_model()
    user = User.objects.get(username="tg_12345")
    profile = user.profile
    assert profile.telegram_id == 12345
    assert user.first_name == "Иван"
    assert user.last_name == "Петров"


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
    tokens = response.json()
    assert tokens["access"]
    assert tokens["refresh"]

    existing.refresh_from_db()
    assert existing.profile.telegram_id == 777
    assert User.objects.filter(username="existing").count() == 1
    assert not User.objects.filter(username="tg_777").exists()