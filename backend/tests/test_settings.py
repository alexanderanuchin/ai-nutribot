from nutribot.settings import _load_telegram_bot_token


def test_load_telegram_bot_token_uses_bot_token_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "fallback-token")

    token, source = _load_telegram_bot_token()

    assert token == "fallback-token"
    assert source == "env:BOT_TOKEN"


def test_load_telegram_bot_token_prefers_specific_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "primary-token")
    monkeypatch.setenv("BOT_TOKEN", "fallback-token")

    token, source = _load_telegram_bot_token()

    assert token == "primary-token"
    assert source == "env:TELEGRAM_BOT_TOKEN"