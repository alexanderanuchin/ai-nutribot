from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..source_blueprints import get_feed_blueprint
from .json import JSONAdapterError, parse_json_feed
from .rss import RSSAdapterError, parse_rss_feed

if TYPE_CHECKING:  # pragma: no cover - hints only
    from ..ingestion import FeedSourceConfig


class FeedAdapterError(RuntimeError):
    """Raised when a feed payload cannot be parsed into the expected structure."""


def parse_feed_response(
    response: Any,
    *,
    source: "FeedSourceConfig",
    rid: str,
) -> dict[str, Any]:
    """Return a normalized feed payload regardless of the upstream format."""

    blueprint_key = getattr(source, "blueprint_name", None) or source.name
    blueprint = get_feed_blueprint(blueprint_key)
    format_hint = blueprint.format if blueprint else "auto"

    data: Any | None = None
    json_error: Exception | None = None

    if format_hint in {"auto", "json"}:
        try:
            data = response.json()
        except ValueError as exc:
            json_error = exc
            if format_hint == "json":
                raise FeedAdapterError("expected JSON feed but parsing failed") from exc
        else:
            if blueprint and blueprint.json:
                try:
                    return parse_json_feed(
                        data,
                        blueprint=blueprint.json,
                        source_name=source.name,
                    )
                except JSONAdapterError as exc:
                    raise FeedAdapterError(str(exc)) from exc
            if isinstance(data, list):
                return {"items": data}
            if isinstance(data, dict):
                return data
            raise FeedAdapterError(
                "feed response JSON must be an object or list of items",
            )

    if format_hint == "json" and data is None and json_error is not None:
        raise FeedAdapterError("JSON feed could not be parsed") from json_error

    # Fallback to RSS/Atom using the adapter.
    try:
        text = response.text
    except AttributeError as exc:  # pragma: no cover - defensive
        raise FeedAdapterError("feed response does not expose text for parsing") from exc

    try:
        return parse_rss_feed(
            text,
            source_name=source.name,
            blueprint=blueprint.rss if blueprint else None,
        )
    except RSSAdapterError as exc:
        raise FeedAdapterError(str(exc)) from exc