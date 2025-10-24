from __future__ import annotations

import html
import logging
import re
import unicodedata
from typing import Any, Mapping

from django.conf import settings

from nutribot.middleware import get_request_id

from .translation import (
    TranslationService,
    TranslationServiceError,
    detect_language,
    get_translation_service,
)

logger = logging.getLogger("feed.ingest.normalize")

_TITLE_MAX_LENGTH = 240
_CONTROL_CHARS_RE = re.compile(r"[\u0000-\u0008\u000B-\u000C\u000E-\u001F\u007F]")
_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_RE = re.compile(r"[ \t\f\v]+")


def normalize_and_translate_article(
    payload: Mapping[str, Any],
    *,
    rid: str | None = None,
    translation_service: TranslationService | None = None,
) -> dict[str, Any]:
    """Clean incoming article fields and ensure Russian content."""

    rid_value = rid or get_request_id()
    raw_title = _coerce_to_string(payload.get("title"))
    raw_lead = _coerce_to_string(payload.get("lead"))
    raw_body = _coerce_to_string(payload.get("body"))

    title_clean = _normalize_text(raw_title, collapse_whitespace=True)
    lead_clean = _normalize_text(raw_lead, collapse_whitespace=True)
    body_clean = _normalize_text(raw_body, collapse_whitespace=False)

    title_clean = _truncate(title_clean or raw_title, _TITLE_MAX_LENGTH)
    lead_clean = lead_clean or raw_lead
    body_clean = body_clean or raw_body

    detection_sample = [value for value in (title_clean, lead_clean, body_clean) if value]
    detected_lang = detect_language(detection_sample) or "und"
    normalized_lang = detected_lang.lower() if detected_lang else "und"
    source_for_provider = normalized_lang if normalized_lang not in {"", "und"} else None

    target_lang = (getattr(settings, "TRANSLATE_TARGET_LANG", "ru") or "ru").lower()
    translation_enabled = getattr(settings, "FEED_TRANSLATE_RU_ENABLED", False)
    needs_translation = (
        translation_enabled
        and target_lang
        and bool(detection_sample)
        and source_for_provider != target_lang
    )

    translated = False
    provider_name: str | None = None
    title_orig: str | None = None
    lead_orig: str | None = None
    body_orig: str | None = None

    if needs_translation:
        service = translation_service or get_translation_service()
        if not service.is_available:
            logger.info(
                "no translation providers configured",
                extra={"rid": rid_value},
            )
        else:
            try:
                outcome = service.translate_texts(
                    [title_clean, lead_clean or "", body_clean or ""],
                    source_lang=source_for_provider,
                    target_lang=target_lang,
                    rid=rid_value,
                )
            except TranslationServiceError as exc:
                logger.warning(
                    "translation failed, falling back to originals",
                    extra={"rid": rid_value, "error": str(exc)},
                )
            else:
                translated_values = outcome.texts
                provider_name = outcome.provider
                if provider_name:
                    translated = True
                    title_orig = title_clean
                    lead_orig = lead_clean
                    body_orig = body_clean
                    title_clean = _truncate(translated_values[0] if translated_values else title_clean, _TITLE_MAX_LENGTH)
                    if len(translated_values) > 1:
                        lead_clean = translated_values[1]
                    if len(translated_values) > 2:
                        body_clean = translated_values[2]

    result = {
        "title": title_clean or raw_title,
        "lead": lead_clean or raw_lead,
        "body": body_clean or raw_body,
        "title_orig": title_orig,
        "lead_orig": lead_orig,
        "body_orig": body_orig,
        "lang": normalized_lang or "und",
        "translated": translated,
        "translation_provider": provider_name or "",
    }
    return result


def _coerce_to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_text(value: str, *, collapse_whitespace: bool) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub(" ", text)
    if collapse_whitespace:
        text = _WHITESPACE_RE.sub(" ", text)
    else:
        text = _SPACE_RE.sub(" ", text)
    return text.strip()


def _truncate(value: str, limit: int) -> str:
    if not value:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()