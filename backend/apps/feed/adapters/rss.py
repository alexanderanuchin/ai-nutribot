from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone as dt_timezone
from typing import Any

import feedparser

from ..source_blueprints import RSSBlueprint


class RSSAdapterError(RuntimeError):
    """Raised when RSS/Atom payload cannot be converted."""


_IMG_SRC_RE = re.compile(r"<img[^>]+?(?:src|data-src)=[\"']([^\"'>]+)[\"']", re.IGNORECASE)


def parse_rss_feed(
    payload: str | bytes,
    *,
    source_name: str,
    blueprint: RSSBlueprint | None = None,
) -> dict[str, Any]:
    """Convert RSS/Atom XML into the canonical feed ingestion payload."""

    parsed = feedparser.parse(payload)
    if parsed.bozo and not parsed.entries:
        raise RSSAdapterError("failed to parse RSS/Atom payload")

    effective_blueprint = blueprint or RSSBlueprint(source_name=None)
    feed_title = (
        getattr(parsed.feed, "title", None)
        or effective_blueprint.source_name
        or source_name
    )

    items: list[dict[str, Any]] = []

    for index, entry in enumerate(getattr(parsed, "entries", [])):
        link = _pick_first(entry, "link", "id", default="")
        if not link:
            # Without a link we cannot build a valid payload – skip the entry.
            continue

        external_id = (
            _pick_first(entry, "id", "guid", default="")
            or link
            or f"{source_name}:{index}"
        )

        title = (entry.get("title") or "").strip() or str(external_id)
        summary = _extract_summary(entry, effective_blueprint) or title
        published_at = _extract_datetime(entry).isoformat()
        categories = _extract_categories(entry)
        image_url = _extract_image(entry, effective_blueprint, summary)

        items.append(
            {
                "external_id": str(external_id),
                "title": title,
                "description": summary.strip(),
                "url": str(link),
                "publishedAt": published_at,
                "sourceName": feed_title,
                "categories": categories,
                "sentiment": None,
                "imageUrl": image_url,
                "toxicity_score": None,
                "clickbait_score": None,
            }
        )

    if not items and parsed.bozo:
        raise RSSAdapterError("RSS/Atom payload contained no usable entries")

    return {"items": items}


def _pick_first(entry: Any, *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = entry.get(key)
        if value:
            return value
    return default


def _extract_summary(entry: Any, blueprint: RSSBlueprint) -> str:
    if blueprint.prefer_content:
        for key in blueprint.summary_fields:
            value = _coerce_entry_text(entry.get(key))
            if value:
                return value
    return _coerce_entry_text(entry.get("summary")) or _coerce_entry_text(entry.get("description")) or ""


def _coerce_entry_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        for item in value:
            text = _coerce_entry_text(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        return (
            value.get("value")
            or value.get("content")
            or value.get("summary")
            or ""
        )
    return str(value)


def _extract_datetime(entry: Any) -> datetime:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(attr)
        if value:
            return datetime.fromtimestamp(calendar.timegm(value), tz=dt_timezone.utc)
    return datetime.now(tz=dt_timezone.utc)


def _extract_categories(entry: Any) -> list[str]:
    categories: list[str] = []
    for tag in entry.get("tags", []) or []:
        term = tag.get("term")
        if term:
            categories.append(term.strip())
    return sorted({cat.lower() for cat in categories if cat})


def _extract_image(entry: Any, blueprint: RSSBlueprint, summary: str) -> str | None:
    for key in blueprint.image_fields:
        value = entry.get(key)
        url = _extract_image_from_value(value)
        if url:
            return url

    if blueprint.fallback_image_from_html:
        for key in blueprint.summary_fields:
            html = _coerce_entry_text(entry.get(key))
            url = _find_img_src(html)
            if url:
                return url
        url = _find_img_src(summary)
        if url:
            return url
    return None


def _extract_image_from_value(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, list):
        for item in value:
            url = _extract_image_from_value(item)
            if url:
                return url
        return None
    if isinstance(value, dict):
        for key in ("url", "href", "src"):
            url = value.get(key)
            if url:
                return str(url)
        return None
    return str(value)


def _find_img_src(html: str) -> str | None:
    if not html:
        return None
    match = _IMG_SRC_RE.search(html)
    if match:
        return match.group(1)
    return None