import pytest

from nutribot.settings import (
    _extend_allowed_hosts,
    _extract_hosts_from_urls,
    _load_telegram_bot_token,
    _parse_allowed_hosts,
)


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


def test_extract_hosts_from_urls_supports_webapp_and_cors_domains():
    origins = "https://example.com, http://sub.domain.local:8080 ,feed.local"

    hosts = _extract_hosts_from_urls(origins)

    assert hosts == {"example.com", "sub.domain.local:8080", "feed.local"}


def test_extract_hosts_from_urls_skips_wildcard_domains():
    hosts = _extract_hosts_from_urls(
        ",".join(
            [
                "https://*.cloudpub.ru",
                "https://*.caloiq.ru",
                "https://exact.cloudpub.ru",
                "https://exact.caloiq.ru",
            ]
        )
    )

    assert hosts == {"exact.cloudpub.ru", "exact.caloiq.ru"}


def test_parse_allowed_hosts_keeps_defaults_without_env_extensions():
    hosts = _parse_allowed_hosts(
        None,
        allow_wildcard=False,
    )

    assert "backend" in hosts  # defaults retained


def test_parse_allowed_hosts_rejects_wildcard_when_not_allowed():
    with pytest.raises(RuntimeError):
        _parse_allowed_hosts("*,example.com", allow_wildcard=False)


def test_extend_allowed_hosts_injects_env_hosts():
    base_hosts = _parse_allowed_hosts(None, allow_wildcard=False)

    merged = _extend_allowed_hosts(
        base_hosts,
        (
            "adversely-congruent-viper.cloudpub.ru",
            "beta.caloiq.ru",
        ),
    )

    assert "backend" in merged
    assert "adversely-congruent-viper.cloudpub.ru" in merged
    assert "beta.caloiq.ru" in merged


def test_extend_allowed_hosts_preserves_wildcard():
    merged = _extend_allowed_hosts(["*"], ("example.com",))

    assert merged == ["*"]
