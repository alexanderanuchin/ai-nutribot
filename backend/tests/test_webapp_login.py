import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest


def build_init_data(bot_token: str, payload: dict) -> str:
    data = payload.copy()
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.mark.django_db
def test_webapp_login_succeeds_with_header_and_body(client, settings):
    settings.TELEGRAM_BOT_TOKEN = "bot-token"
    user_payload = {"id": 222, "first_name": "Test"}
    raw_payload = {
        "auth_date": "1700000000",
        "query_id": "AAEAAQ",
        "user": json.dumps(user_payload, separators=(",", ":"), ensure_ascii=False),
    }
    init_data = build_init_data(settings.TELEGRAM_BOT_TOKEN, raw_payload)

    response = client.post(
        "/api/auth/webapp/login/",
        {"init_data": init_data},
        HTTP_X_TELEGRAM_INIT_DATA=init_data,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["telegram_user_id"] == 222
    

@pytest.mark.django_db
def test_webapp_login_falls_back_to_body_when_header_invalid(client, settings):
    settings.TELEGRAM_BOT_TOKEN = "bot-token"
    user_payload = {"id": 333, "first_name": "Fallback"}
    raw_payload = {
        "auth_date": "1700000000",
        "query_id": "AAEAAQ",
        "user": json.dumps(user_payload, separators=(",", ":"), ensure_ascii=False),
    }
    init_data = build_init_data(settings.TELEGRAM_BOT_TOKEN, raw_payload)
    truncated_header = init_data[:20]

    response = client.post(
        "/api/auth/webapp/login/",
        {"init_data": init_data},
        HTTP_X_TELEGRAM_INIT_DATA=truncated_header,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["telegram_user_id"] == 333