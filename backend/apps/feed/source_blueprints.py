from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping


@dataclass(frozen=True)
class RSSBlueprint:
    """Options for parsing RSS/Atom feeds."""

    source_name: str | None = None
    prefer_content: bool = True
    fallback_image_from_html: bool = True
    summary_fields: tuple[str, ...] = ("content", "summary", "description")
    image_fields: tuple[str, ...] = ("media_content", "media_thumbnail", "image", "enclosures")


@dataclass(frozen=True)
class JSONBlueprint:
    """Options for parsing JSON feeds with declarative field mappings."""

    items_paths: tuple[str, ...]
    field_map: Mapping[str, tuple[str, ...]]
    categories_paths: tuple[str, ...] = ()
    image_paths: tuple[str, ...] = ()
    slug_paths: tuple[str, ...] = ()
    url_prefix: str | None = None
    default_source_name: str | None = None


@dataclass(frozen=True)
class FeedBlueprint:
    """A blueprint describing how to adapt a feed into the canonical payload."""

    format: Literal["rss", "json", "auto"] = "auto"
    rss: RSSBlueprint | None = None
    json: JSONBlueprint | None = None


_BLUEPRINTS: Mapping[str, FeedBlueprint] = {
    # Nutrition and safety focused RSS feeds (WordPress/standard RSS patterns)
    "harvard-nutrition-source": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="The Nutrition Source"),
    ),
    "bon-appetit": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Bon Appétit"),
    ),
    "epicurious": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Epicurious"),
    ),
    "guardian-food": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="The Guardian – Food"),
    ),
    "food52-blog": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Food52"),
    ),
    "serious-eats": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Serious Eats"),
    ),
    "fao-newsroom": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="FAO Newsroom"),
    ),
    "efsa-news": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="EFSA"),
    ),
    "anses-actualites": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="ANSES"),
    ),
    "lebensmittelwarnung-hessen": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Lebensmittelwarnung Hessen"),
    ),
    "foodsafetynews": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Food Safety News"),
    ),
    "euractiv-agrifood": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="Euractiv – Agrifood"),
    ),
    "cfs-hongkong-whatsnew": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="CFS Hong Kong"),
    ),
    "fsanz-news": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="FSANZ"),
    ),
    "foodsafety-gov-recalls": FeedBlueprint(
        format="rss",
        rss=RSSBlueprint(source_name="FoodSafety.gov Recalls"),
    ),
    "who-news": FeedBlueprint(
        format="json",
        json=JSONBlueprint(
            items_paths=("value", "results", "news", "items", ""),
            field_map={
                "external_id": ("id", "storyId", "newsId"),
                "title": ("title", "headline"),
                "description": ("summary", "teaser", "description"),
                "url": ("url", "externalLink"),
                "publishedAt": ("date", "publishedDate"),
                "updatedAt": ("lastModified",),
                "sourceName": ("source.name", "source"),
            },
            categories_paths=("topics[].title", "categories[].title"),
            image_paths=("image.url", "thumbnail.url", "mainImage.url"),
            slug_paths=("slug", "path"),
            url_prefix="https://www.who.int/",
            default_source_name="WHO",
        ),
    ),
}

# Provide a few aliases for convenience so configs can use alternative identifiers.
_ALIASES: Mapping[str, str] = {
    "the-nutrition-source": "harvard-nutrition-source",
    "harvard-nutrition": "harvard-nutrition-source",
    "bonappetit": "bon-appetit",
    "guardian-food": "guardian-food",
    "food52": "food52-blog",
    "seriouseats": "serious-eats",
    "who": "who-news",
}


def get_feed_blueprint(name: str) -> FeedBlueprint | None:
    """Return a blueprint for a configured source if available."""

    key = name.lower()
    canonical = _ALIASES.get(key, key)
    return _BLUEPRINTS.get(canonical)