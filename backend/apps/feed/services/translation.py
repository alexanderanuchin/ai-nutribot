from __future__ import annotations

import hashlib
import html
import logging
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

import httpx
from django.conf import settings

try:  # pragma: no cover - optional dependency (pycld3 replaced with gcld3)
    import gcld3
except ImportError:  # pragma: no cover - library optional
    gcld3 = None  # type: ignore[assignment]
    NNetLanguageIdentifier = None  # type: ignore[assignment]
else:  # pragma: no cover - available dependency
    NNetLanguageIdentifier = gcld3.NNetLanguageIdentifier

try:  # pragma: no cover - optional dependency
    from langdetect import DetectorFactory, LangDetectException, detect
except ImportError:  # pragma: no cover - library optional
    DetectorFactory = None  # type: ignore
    LangDetectException = Exception  # type: ignore
    detect = None  # type: ignore
else:  # pragma: no cover - configuration
    DetectorFactory.seed = 42

try:  # pragma: no cover - optional dependency
    import redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - redis optional
    redis = None  # type: ignore

    class RedisError(Exception):
        """Fallback Redis error when package is not available."""

from nutribot.middleware import get_request_id

logger = logging.getLogger("feed.translation")
translate_logger = logging.getLogger("feed.translate.yandex")

_LANGUAGE_IDENTIFIER = None
if NNetLanguageIdentifier is not None:  # pragma: no cover - slow path
    _LANGUAGE_IDENTIFIER = NNetLanguageIdentifier(min_num_bytes=0, max_num_bytes=3000)

_MAX_TRANSLATABLE_LENGTH = 10_000
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 180  # 180 days

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_ALPHA_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _is_mostly_cyrillic(value: str) -> bool:
    letters = _ALPHA_RE.findall(value)
    if not letters:
        return False
    cyrillic = _CYRILLIC_RE.findall("".join(letters))
    return len(cyrillic) / len(letters) >= 0.5


class TranslationProviderError(RuntimeError):
    """Raised when a translation provider cannot fulfil the request."""


class TranslationProviderConfigurationError(TranslationProviderError):
    """Raised when provider configuration is invalid or incomplete."""


@dataclass(slots=True)
class TranslationOutcome:
    texts: list[str]
    provider: str | None
    source_lang: str | None


class TranslationProvider:
    """Base translation provider interface."""

    name: str = "provider"

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str,
    ) -> list[str]:  # pragma: no cover - interface
        raise NotImplementedError


class YandexProvider(TranslationProvider):
    name = "yandex"

    def __init__(
        self,
        *,
        api_key: str | None,
        folder_id: str | None,
        timeout: float = 8.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.folder_id = (folder_id or "").strip()
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.max_chunk_chars = 3000
        self.min_chunk_chars = 1500
        self.max_batch_texts = 25
        self.max_batch_chars = 15_000
        self.max_retries = 3
        self.backoff_intervals = [0.5, 1.0, 2.0]
        self._timeout = httpx.Timeout(timeout, connect=3.0, read=5.0, write=5.0)
        if http_client is None:
            self._client = httpx.Client(timeout=self._timeout)
            self._owns_client = True
        else:
            self._client = http_client
            self._owns_client = False
        self._headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str,
    ) -> list[str]:
        if not self.api_key or not self.folder_id:
            raise TranslationProviderConfigurationError("Yandex Translate credentials are incomplete")
        if not texts:
            return []

        normalized_texts = [text if text is not None else "" for text in texts]
        format_hint = self._detect_format(normalized_texts)

        segments, index_map = self._split_segments(normalized_texts)
        if not segments:
            return ["" for _ in normalized_texts]

        translated_segments: list[str] = []
        source_code = source_lang or "auto"
        for batch in self._iter_batches(segments):
            translated_segments.extend(
                self._request_with_retries(
                    batch,
                    target_lang=target_lang,
                    source_lang=source_code,
                    rid=rid,
                    format_hint=format_hint,
                )
            )

        if len(translated_segments) != len(segments):
            raise TranslationProviderError("Yandex Translate returned unexpected results")

        results: list[str] = []
        for original_text, (start, count) in zip(normalized_texts, index_map):
            if count == 0:
                results.append(original_text)
                continue
            end = start + count
            translated_value = "".join(translated_segments[start:end])
            results.append(translated_value)
        return results

    def _detect_format(self, texts: Sequence[str]) -> str:
        for text in texts:
            if text and _HTML_TAG_RE.search(text):
                return "HTML"
        return "PLAIN_TEXT"

    def _split_segments(self, texts: Sequence[str]) -> tuple[list[str], list[tuple[int, int]]]:
        segments: list[str] = []
        index_map: list[tuple[int, int]] = []
        for text in texts:
            if not text:
                index_map.append((len(segments), 0))
                continue
            chunks = self._chunk_text(text)
            index_map.append((len(segments), len(chunks)))
            segments.extend(chunks)
        return segments, index_map

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]
        parts: list[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + self.max_chunk_chars)
            if end < length:
                split = text.rfind("\n", start + self.min_chunk_chars, end)
                if split == -1:
                    split = text.rfind(" ", start + self.min_chunk_chars, end)
                if split == -1:
                    split = end
            else:
                split = end
            if split <= start:
                split = min(length, start + self.max_chunk_chars)
            parts.append(text[start:split])
            start = split
        return parts

    def _iter_batches(self, segments: Sequence[str]) -> Iterable[list[str]]:
        batch: list[str] = []
        char_count = 0
        for segment in segments:
            segment_len = len(segment)
            if batch and (
                len(batch) >= self.max_batch_texts
                or char_count + segment_len > self.max_batch_chars
            ):
                yield batch
                batch = []
                char_count = 0
            batch.append(segment)
            char_count += segment_len
        if batch:
            yield batch

    def _request_with_retries(
        self,
        texts: Sequence[str],
        *,
        target_lang: str,
        source_lang: str,
        rid: str,
        format_hint: str,
    ) -> list[str]:
        payload: dict[str, object] = {
            "folderId": self.folder_id,
            "targetLanguageCode": target_lang,
            "texts": list(texts),
            "sourceLanguageCode": source_lang,
            "format": format_hint,
        }
        total_bytes = sum(len(text.encode("utf-8")) for text in texts)
        attempts = self.max_retries
        for attempt in range(attempts):
            start_time = time.perf_counter()
            status_code: int | None = None
            try:
                response = self._client.post(self.base_url, json=payload, headers=self._headers)
                status_code = response.status_code
                response.raise_for_status()
                data = response.json()
                translations = [str(item.get("text", "")) for item in data.get("translations", [])]
                duration = time.perf_counter() - start_time
                rps = 1.0 / duration if duration > 0 else 0.0
                translate_logger.info(
                    "translation request completed",
                    extra={
                        "rid": rid,
                        "status": status_code,
                        "provider": self.name,
                        "bytes": total_bytes,
                        "rps": round(rps, 4),
                        "attempt": attempt + 1,
                    },
                )
                if len(translations) != len(texts):
                    raise TranslationProviderError("Yandex Translate returned unexpected results")
                return translations
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError) as exc:
                duration = time.perf_counter() - start_time
                if status_code is None and isinstance(exc, httpx.HTTPStatusError):
                    status_code = exc.response.status_code if exc.response else None
                translate_logger.warning(
                    "translation request failed",
                    extra={
                        "rid": rid,
                        "status": status_code,
                        "provider": self.name,
                        "bytes": total_bytes,
                        "attempt": attempt + 1,
                        "duration": round(duration, 4),
                        "error": str(exc),
                    },
                )
                if attempt >= attempts - 1:
                    raise TranslationProviderError("Yandex translation failed") from exc
                delay = self.backoff_intervals[min(attempt, len(self.backoff_intervals) - 1)]
                time.sleep(delay)


class TranslationCache:
    """Redis-backed translation cache with in-memory fallback."""

    def __init__(self, *, ttl_seconds: int = _CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._client = None
        self._client_lock = threading.Lock()
        self._client_initialised = False
        self._local_cache: dict[str, tuple[float, str]] = {}

    def _get_client(self):  # pragma: no cover - thin wrapper
        if not redis:
            return None
        with self._client_lock:
            if self._client_initialised:
                return self._client
            url = getattr(settings, "REDIS_URL", "")
            if url:
                try:
                    self._client = redis.Redis.from_url(url, decode_responses=True)
                except Exception as exc:  # pragma: no cover - connection issues
                    logger.warning(
                        "redis connection for translation cache failed",
                        extra={"rid": get_request_id(), "error": str(exc)},
                    )
                    self._client = None
            self._client_initialised = True
            return self._client

    @staticmethod
    def _key(provider: str, source_lang: str | None, target_lang: str, text: str) -> str:
        source = source_lang or "auto"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"tr:{provider}:{source}:{target_lang}:{digest}"

    def get(self, *, provider: str, source_lang: str | None, target_lang: str, text: str, rid: str) -> str | None:
        key = self._key(provider, source_lang, target_lang, text)
        client = self._get_client()
        if client is not None:
            try:
                value = client.get(key)
            except RedisError as exc:  # pragma: no cover - rare
                logger.warning(
                    "translation cache redis get failed",
                    extra={"rid": rid, "error": str(exc)},
                )
                value = None
            if value is not None:
                return value
        with self._client_lock:
            entry = self._local_cache.get(key)
            if not entry:
                return None
            expires_at, cached_value = entry
            if expires_at < time.time():
                self._local_cache.pop(key, None)
                return None
            return cached_value

    def set(
        self,
        *,
        provider: str,
        source_lang: str | None,
        target_lang: str,
        text: str,
        value: str,
        rid: str,
    ) -> None:
        key = self._key(provider, source_lang, target_lang, text)
        client = self._get_client()
        if client is not None:
            try:
                client.setex(key, self.ttl_seconds, value)
            except RedisError as exc:  # pragma: no cover - rare
                logger.warning(
                    "translation cache redis set failed",
                    extra={"rid": rid, "error": str(exc)},
                )
        with self._client_lock:
            self._local_cache[key] = (time.time() + self.ttl_seconds, value)


class TranslationServiceError(RuntimeError):
    """Raised when translation fails across all providers."""


class TranslationService:
    """Service coordinating language detection, caching and translation."""

    def __init__(
        self,
        *,
        provider: TranslationProvider | None,
        cache: TranslationCache | None = None,
    ) -> None:
        self.provider = provider
        self.cache = cache or TranslationCache()

    @property
    def is_available(self) -> bool:
        return self.provider is not None

    @classmethod
    def from_settings(cls) -> "TranslationService":
        api_key = getattr(settings, "YANDEX_API_KEY", "").strip()
        folder_id = getattr(settings, "YANDEX_FOLDER_ID", "").strip()
        providers = tuple(
            provider.strip().lower()
            for provider in getattr(settings, "TRANSLATE_PROVIDERS", ("yandex",))
            if provider
        )
        provider: TranslationProvider | None = None
        rid = get_request_id()
        if "yandex" in providers:
            if not api_key or not folder_id:
                logger.error(
                    "yandex translation credentials missing",
                    extra={"rid": rid},
                )
            else:
                provider = YandexProvider(api_key=api_key, folder_id=folder_id)
        elif providers:
            logger.warning(
                "unsupported translation provider configured",
                extra={"rid": rid, "providers": providers},
            )
        return cls(provider=provider)

    def translate_texts(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str | None = None,
    ) -> TranslationOutcome:
        rid_value = rid or get_request_id()
        sanitized = [self._prepare_text(text) for text in texts]
        if not sanitized:
            return TranslationOutcome(texts=[], provider=None, source_lang=source_lang)
        # If translation is not required return original texts.
        if not target_lang:
            return TranslationOutcome(texts=list(sanitized), provider=None, source_lang=source_lang)
        pending_indices = [idx for idx, value in enumerate(sanitized) if value]
        if not pending_indices:
            return TranslationOutcome(texts=list(sanitized), provider=None, source_lang=source_lang)
        for index in list(pending_indices):
            if _is_mostly_cyrillic(sanitized[index]):
                pending_indices.remove(index)
        if not pending_indices:
            return TranslationOutcome(texts=list(sanitized), provider=None, source_lang=source_lang)
        provider = self.provider
        if provider is None:
            logger.info(
                "translation provider is not configured",
                extra={"rid": rid_value},
            )
            raise TranslationServiceError("Translation provider is not configured")

        results = list(sanitized)
        effective_source = source_lang or None

        cached_hits: list[int] = []
        for index in list(pending_indices):
            cached = self.cache.get(
                provider=provider.name,
                source_lang=effective_source,
                target_lang=target_lang,
                text=sanitized[index],
                rid=rid_value,
            )
            if cached is not None:
                results[index] = cached
                cached_hits.append(index)
        for index in cached_hits:
            pending_indices.remove(index)

        if not pending_indices:
            return TranslationOutcome(texts=results, provider=provider.name, source_lang=effective_source)

        try:
            translated_values = provider.translate(
                [sanitized[index] for index in pending_indices],
                source_lang=effective_source,
                target_lang=target_lang,
                rid=rid_value,
            )
        except TranslationProviderConfigurationError as exc:
            logger.info(
                "translation provider configuration invalid",
                extra={"rid": rid_value, "provider": provider.name, "error": str(exc)},
            )
            raise TranslationServiceError("Translation provider configuration invalid") from exc
        except TranslationProviderError as exc:
            logger.warning(
                "translation provider failed",
                extra={"rid": rid_value, "provider": provider.name, "error": str(exc)},
            )
            raise TranslationServiceError("Translation request failed") from exc

        if len(translated_values) != len(pending_indices):
            logger.warning(
                "translation provider returned mismatched results",
                extra={"rid": rid_value, "provider": provider.name},
            )
            raise TranslationServiceError("Translation provider returned mismatched results")

        for index, value in zip(pending_indices, translated_values):
            results[index] = value
            self.cache.set(
                provider=provider.name,
                source_lang=effective_source,
                target_lang=target_lang,
                text=sanitized[index],
                value=value,
                rid=rid_value,
            )

        return TranslationOutcome(texts=results, provider=provider.name, source_lang=effective_source)

    @staticmethod
    def _prepare_text(text: str | None) -> str:
        if not text:
            return ""
        value = unicodedata.normalize("NFC", html.unescape(text))
        return value[:_MAX_TRANSLATABLE_LENGTH]


def detect_language(payload: Iterable[str]) -> str | None:
    """Detect language using CLD3 with langdetect fallback."""

    sample = " ".join(part for part in payload if part).strip()
    if not sample:
        return None
    if _LANGUAGE_IDENTIFIER is not None:  # pragma: no cover - heavy
        try:
            result = _LANGUAGE_IDENTIFIER.FindLanguage(sample)
        except Exception:  # pragma: no cover - defensive
            result = None
        if result and result.is_reliable and result.language not in {"und", ""}:
            return result.language.lower()
    if detect is not None:
        try:
            language = detect(sample)
        except LangDetectException:  # pragma: no cover - unreliable input
            return None
        return language.lower()
    return None


_translation_service: TranslationService | None = None
_service_lock = threading.Lock()


def get_translation_service() -> TranslationService:
    global _translation_service
    if _translation_service is None:
        with _service_lock:
            if _translation_service is None:
                _translation_service = TranslationService.from_settings()
    return _translation_service


def reset_translation_service() -> None:
    global _translation_service
    with _service_lock:
        _translation_service = None
