from __future__ import annotations

import httpx
import pytest

from apps.feed.services.translation import (
    TranslationProviderError,
    YandexProvider,
)


class _DummyResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._data


class _DummyClient:
    def __init__(self, *, fail_times: int = 0) -> None:
        self.calls: list[dict] = []
        self.fail_times = fail_times

    def post(self, url: str, *, json: dict, headers: dict):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.fail_times > 0:
            self.fail_times -= 1
            request = httpx.Request("POST", url)
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)
        translations = [{"text": text.upper()} for text in json["texts"]]
        return _DummyResponse(200, {"translations": translations})


def test_yandex_provider_translates_chunks_and_preserves_order(monkeypatch):
    client = _DummyClient()
    provider = YandexProvider(api_key="key", folder_id="folder", http_client=client)
    provider.max_chunk_chars = 10
    provider.min_chunk_chars = 5
    provider.max_batch_texts = 3
    provider.max_batch_chars = 24

    texts = ["", "<p>Hello world</p>", "a" * 25]
    result = provider.translate(texts, source_lang="en", target_lang="ru", rid="rid-1")

    assert result[0] == ""
    assert result[1] == "<P>HELLO WORLD</P>"
    assert result[2] == "A" * 25
    assert client.calls[0]["json"]["format"] == "HTML"
    total_segments = sum(len(call["json"]["texts"]) for call in client.calls)
    assert total_segments >= 3


def test_yandex_provider_retries_and_raises(monkeypatch):
    client = _DummyClient(fail_times=3)
    provider = YandexProvider(api_key="key", folder_id="folder", http_client=client)
    provider.max_retries = 3
    monkeypatch.setattr("apps.feed.services.translation.time.sleep", lambda _: None)

    with pytest.raises(TranslationProviderError):
        provider.translate(["hello"], source_lang="en", target_lang="ru", rid="rid-2")

    assert len(client.calls) == 3