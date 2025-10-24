from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
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

_LANGUAGE_IDENTIFIER = None
if NNetLanguageIdentifier is not None:  # pragma: no cover - slow path
    _LANGUAGE_IDENTIFIER = NNetLanguageIdentifier(min_num_bytes=0, max_num_bytes=3000)

_MAX_TRANSLATABLE_LENGTH = 10_000
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 180  # 180 days


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


class DeepLProvider(TranslationProvider):
    name = "deepl"

    def __init__(self, *, api_key: str | None, base_url: str | None = None, timeout: float = 10.0):
        self.api_key = api_key or ""
        self.base_url = base_url or "https://api-free.deepl.com/v2/translate"
        self.timeout = timeout

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str,
    ) -> list[str]:
        if not self.api_key:
            raise TranslationProviderConfigurationError("DeepL API key is not configured")
        payload = [("auth_key", self.api_key), ("target_lang", target_lang.upper())]
        if source_lang:
            payload.append(("source_lang", source_lang.upper()))
        for text in texts:
            payload.append(("text", text))
        try:
            response = httpx.post(self.base_url, data=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            translations = data.get("translations") or []
            if len(translations) != len(texts):
                raise TranslationProviderError("DeepL returned unexpected number of translations")
            return [str(item.get("text", "")) for item in translations]
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "deepl translation failed",
                extra={"rid": rid, "error": str(exc)},
            )
            raise TranslationProviderError("DeepL translation failed") from exc


class GoogleProvider(TranslationProvider):
    name = "google"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        project_id: str | None = None,
        credentials_json_b64: str | None = None,
        location: str = "global",
        timeout: float = 10.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.project_id = (project_id or "").strip()
        self.credentials_json_b64 = (credentials_json_b64 or "").strip()
        self.location = location
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        if self.credentials_json_b64:
            try:
                decoded = base64.b64decode(self.credentials_json_b64).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise TranslationProviderConfigurationError("Google credentials are invalid") from exc
            credentials = json.loads(decoded)
            token = credentials.get("access_token")
            if not token:
                raise TranslationProviderConfigurationError("Google credentials missing access token")
            return {"Authorization": f"Bearer {token}"}
        if self.api_key:
            return {}
        raise TranslationProviderConfigurationError("Google Translate credentials are not configured")

    def _build_url(self) -> str:
        if self.credentials_json_b64 and self.project_id:
            return (
                f"https://translation.googleapis.com/v3/projects/{self.project_id}/locations/{self.location}:"
                "translateText"
            )
        if self.api_key:
            return f"https://translation.googleapis.com/language/translate/v2?key={self.api_key}"
        raise TranslationProviderConfigurationError("Google Translate configuration is incomplete")

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str,
    ) -> list[str]:
        if not texts:
            return []
        url = self._build_url()
        headers = self._build_headers()
        payload: dict[str, object]
        if url.endswith("translateText"):
            payload = {
                "contents": list(texts),
                "targetLanguageCode": target_lang,
            }
            if source_lang:
                payload["sourceLanguageCode"] = source_lang
        else:
            payload = {
                "q": list(texts),
                "target": target_lang,
            }
            if source_lang:
                payload["source"] = source_lang
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            data = response.json()
            translations = []
            if "data" in data:
                translations = [
                    str(item.get("translatedText", ""))
                    for item in data["data"].get("translations", [])
                ]
            else:
                translations = [
                    str(item.get("translatedText", ""))
                    for item in data.get("translations", [])
                ]
            if len(translations) != len(texts):
                raise TranslationProviderError("Google Translate returned unexpected results")
            return translations
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning(
                "google translation failed",
                extra={"rid": rid, "error": str(exc)},
            )
            raise TranslationProviderError("Google translation failed") from exc


class YandexProvider(TranslationProvider):
    name = "yandex"

    def __init__(
        self,
        *,
        api_key: str | None,
        folder_id: str | None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.folder_id = (folder_id or "").strip()
        self.timeout = timeout
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"

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
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        body: dict[str, object] = {
            "folderId": self.folder_id,
            "texts": list(texts),
            "targetLanguageCode": target_lang,
        }
        if source_lang:
            body["sourceLanguageCode"] = source_lang
        try:
            response = httpx.post(self.base_url, json=body, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            translations = [str(item.get("text", "")) for item in data.get("translations", [])]
            if len(translations) != len(texts):
                raise TranslationProviderError("Yandex Translate returned unexpected results")
            return translations
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning(
                "yandex translation failed",
                extra={"rid": rid, "error": str(exc)},
            )
            raise TranslationProviderError("Yandex translation failed") from exc


class AzureProvider(TranslationProvider):
    name = "azure"

    def __init__(
        self,
        *,
        api_key: str | None,
        region: str | None,
        endpoint: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.region = (region or "").strip()
        self.endpoint = endpoint or "https://api.cognitive.microsofttranslator.com"
        self.timeout = timeout

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_lang: str | None,
        target_lang: str,
        rid: str,
    ) -> list[str]:
        if not self.api_key or not self.region:
            raise TranslationProviderConfigurationError("Azure Translator credentials are incomplete")
        params = {"api-version": "3.0", "to": target_lang}
        if source_lang:
            params["from"] = source_lang
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json",
        }
        body = [{"text": text} for text in texts]
        try:
            response = httpx.post(
                f"{self.endpoint}/translate",
                params=params,
                headers=headers,
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            translations: list[str] = []
            for item in data:
                translations.append(str(item.get("translations", [{}])[0].get("text", "")))
            if len(translations) != len(texts):
                raise TranslationProviderError("Azure Translator returned unexpected results")
            return translations
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning(
                "azure translation failed",
                extra={"rid": rid, "error": str(exc)},
            )
            raise TranslationProviderError("Azure translation failed") from exc


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
    """Service coordinating language detection, caching and provider fallback."""

    def __init__(self, providers: Sequence[TranslationProvider], cache: TranslationCache | None = None) -> None:
        self.providers = list(providers)
        self.cache = cache or TranslationCache()

    @classmethod
    def from_settings(cls) -> "TranslationService":
        providers: list[TranslationProvider] = []
        configured = getattr(settings, "TRANSLATE_PROVIDERS", ())
        for provider_name in configured:
            name = provider_name.strip().lower()
            if not name:
                continue
            provider = None
            if name == "deepl":
                provider = DeepLProvider(api_key=getattr(settings, "DEEPL_API_KEY", ""))
            elif name == "google":
                provider = GoogleProvider(
                    api_key=getattr(settings, "GOOGLE_TRANSLATE_API_KEY", ""),
                    project_id=getattr(settings, "GOOGLE_PROJECT_ID", ""),
                    credentials_json_b64=getattr(settings, "GOOGLE_CREDENTIALS_JSON_BASE64", ""),
                    location=getattr(settings, "GOOGLE_TRANSLATE_LOCATION", "global"),
                )
            elif name == "yandex":
                provider = YandexProvider(
                    api_key=getattr(settings, "YANDEX_API_KEY", ""),
                    folder_id=getattr(settings, "YANDEX_FOLDER_ID", ""),
                )
            elif name == "azure":
                provider = AzureProvider(
                    api_key=getattr(settings, "AZURE_TRANSLATOR_KEY", ""),
                    region=getattr(settings, "AZURE_TRANSLATOR_REGION", ""),
                    endpoint=getattr(settings, "AZURE_TRANSLATOR_ENDPOINT", None),
                )
            if provider is not None:
                providers.append(provider)
        return cls(providers=providers)

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
        results = list(sanitized)
        provider_used: str | None = None
        effective_source = source_lang or None
        for provider in self.providers:
            if not pending_indices:
                break
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
                provider_used = provider_used or provider.name
                break
            try:
                translated_values = provider.translate(
                    [sanitized[index] for index in pending_indices],
                    source_lang=effective_source,
                    target_lang=target_lang,
                    rid=rid_value,
                )
            except TranslationProviderConfigurationError as exc:
                logger.info(
                    "translation provider skipped due to configuration",
                    extra={"rid": rid_value, "provider": provider.name, "error": str(exc)},
                )
                continue
            except TranslationProviderError as exc:
                logger.warning(
                    "translation provider failed",
                    extra={"rid": rid_value, "provider": provider.name, "error": str(exc)},
                )
                continue
            if len(translated_values) != len(pending_indices):
                logger.warning(
                    "translation provider returned mismatched results",
                    extra={"rid": rid_value, "provider": provider.name},
                )
                continue
            provider_used = provider.name
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
            pending_indices = []
            break
        if pending_indices:
            logger.error(
                "translation failed for all providers",
                extra={"rid": rid_value, "providers": [p.name for p in self.providers]},
            )
            raise TranslationServiceError("Translation failed for all providers")
        return TranslationOutcome(texts=results, provider=provider_used, source_lang=effective_source)

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