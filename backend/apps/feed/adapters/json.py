from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any, Iterable
from urllib.parse import urljoin

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..source_blueprints import JSONBlueprint


class JSONAdapterError(RuntimeError):
    """Raised when a JSON feed cannot be normalised."""


def parse_json_feed(
    data: Any,
    *,
    blueprint: JSONBlueprint,
    source_name: str,
) -> dict[str, Any]:
    """Normalise JSON feeds according to a blueprint mapping."""

    items = _resolve_items(data, blueprint.items_paths)
    results: list[dict[str, Any]] = []

    for raw in items:
        if not isinstance(raw, dict):
            continue

        external_id = _extract_scalar(raw, blueprint.field_map.get("external_id", ()))
        if not external_id:
            continue

        title = _extract_scalar(raw, blueprint.field_map.get("title", ())) or str(external_id)
        summary = _extract_scalar(raw, blueprint.field_map.get("description", ())) or title

        url = _extract_scalar(raw, blueprint.field_map.get("url", ()))
        if not url:
            slug = _extract_scalar(raw, blueprint.slug_paths)
            if slug and blueprint.url_prefix:
                url = urljoin(blueprint.url_prefix, slug)
        if not url:
            continue

        published = _extract_datetime(
            _extract_scalar(raw, blueprint.field_map.get("publishedAt", ()))
        )
        if not published:
            published = timezone.now().astimezone(dt_timezone.utc).isoformat()

        source_override = (
            _extract_scalar(raw, blueprint.field_map.get("sourceName", ()))
            or blueprint.default_source_name
            or source_name
        )

        image_url = _extract_scalar(raw, blueprint.image_paths)
        if image_url is not None:
            image_url = str(image_url)
        categories = _extract_categories(raw, blueprint.categories_paths)

        results.append(
            {
                "external_id": str(external_id),
                "title": title.strip(),
                "description": summary.strip(),
                "url": str(url),
                "publishedAt": published,
                "sourceName": str(source_override),
                "categories": categories,
                "sentiment": None,
                "imageUrl": image_url,
                "toxicity_score": None,
                "clickbait_score": None,
            }
        )

    return {"items": results}


def _resolve_items(data: Any, paths: Iterable[str]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data

    for path in paths:
        if not path:
            if isinstance(data, list):
                return data
            continue
        values = _resolve_path_values(data, path)
        for value in values:
            if isinstance(value, list):
                return value
    return []


def _extract_scalar(raw: dict[str, Any], paths: Iterable[str] | None) -> Any:
    if not paths:
        return None
    for path in paths:
        values = _resolve_path_values(raw, path)
        for value in values:
            if isinstance(value, (str, int, float)):
                return value
            if value is not None:
                return value
    return None


def _extract_categories(raw: dict[str, Any], paths: Iterable[str]) -> list[str]:
    categories: list[str] = []
    for path in paths:
        values = _resolve_path_values(raw, path)
        for value in values:
            if isinstance(value, str) and value.strip():
                categories.append(value.strip().lower())
    return sorted(set(categories))


def _extract_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        dt_value = datetime.fromtimestamp(value, tz=dt_timezone.utc)
        return dt_value.isoformat()
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_timezone.utc)
        else:
            parsed = parsed.astimezone(dt_timezone.utc)
        return parsed.isoformat()
    return None


def _resolve_path_values(data: Any, path: str) -> list[Any]:
    segments = [segment for segment in path.split(".") if segment]
    values = [data]
    for segment in segments:
        list_mode = segment.endswith("[]")
        key = segment[:-2] if list_mode else segment
        next_values: list[Any] = []
        for value in values:
            if isinstance(value, dict):
                candidate = value.get(key)
            elif isinstance(value, list):
                if list_mode:
                    for item in value:
                        if isinstance(item, dict) and key in item:
                            next_values.append(item[key])
                    continue
                # Allow traversing into a list even without explicit [] by
                # iterating items – useful for sloppy feeds.
                for item in value:
                    if isinstance(item, dict) and key in item:
                        next_values.append(item[key])
                continue
            else:
                candidate = None

            if candidate is None:
                continue
            if list_mode:
                if isinstance(candidate, list):
                    next_values.extend(candidate)
                elif isinstance(candidate, dict):
                    next_values.extend(candidate.values())
            else:
                next_values.append(candidate)
        values = next_values
    return values