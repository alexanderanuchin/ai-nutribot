from __future__ import annotations

from decimal import Decimal
from decimal import Decimal, InvalidOperation

from typing import Iterable

from django.db import connection
from django.db.models import Q, QuerySet

from .models import DealOffer, NewsArticle, Recipe


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "flagged", "moderated"}:
        return True
    if normalized in {"0", "false", "no", "clean"}:
        return False
    if normalized in {"any", "all", "*"}:
        return None
    return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None


def filter_news(queryset: QuerySet[NewsArticle], params: dict[str, str]) -> QuerySet[NewsArticle]:
    tags = _parse_csv(params.get("tags"))
    if tags:
        queryset = queryset.filter(tags__slug__in=tags)
    search = params.get("search")
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(lead__icontains=search))
    source = params.get("source")
    if source:
        queryset = queryset.filter(source_name__icontains=source)
    tonality = params.get("tonality")
    if tonality in {choice for choice, _ in NewsArticle.Tonality.choices}:
        queryset = queryset.filter(tonality=tonality)
    categories = _parse_csv(params.get("categories") or params.get("source_categories"))
    if categories:
        if connection.vendor == "postgresql":
            queryset = queryset.filter(source_categories__overlap=categories)
        else:
            for category in categories:
                queryset = queryset.filter(source_categories__icontains=category)
    toxicity_min = _parse_decimal(params.get("toxicity_min"))
    if toxicity_min is not None:
        queryset = queryset.filter(toxicity_score__gte=toxicity_min)
    toxicity_max = _parse_decimal(params.get("toxicity_max"))
    if toxicity_max is not None:
        queryset = queryset.filter(toxicity_score__lte=toxicity_max)
    clickbait_min = _parse_decimal(params.get("clickbait_min"))
    if clickbait_min is not None:
        queryset = queryset.filter(clickbait_score__gte=clickbait_min)
    clickbait_max = _parse_decimal(params.get("clickbait_max"))
    if clickbait_max is not None:
        queryset = queryset.filter(clickbait_score__lte=clickbait_max)
    flagged = _parse_bool(params.get("is_flagged"))
    if flagged is True:
        queryset = queryset.filter(is_flagged=True)
    elif flagged is False:
        queryset = queryset.filter(is_flagged=False)
    return queryset.distinct()


def filter_recipes(queryset: QuerySet[Recipe], params: dict[str, str]) -> QuerySet[Recipe]:
    diets = _parse_csv(params.get("diet"))
    allergens = _parse_csv(params.get("exclude_allergens"))
    price_min = params.get("price_min")
    price_max = params.get("price_max")
    cook_time_max = params.get("cook_time_max")
    sort = params.get("sort")

    if diets:
        if connection.vendor == "postgresql":
            queryset = queryset.filter(diet_tags__overlap=diets)
        else:
            for diet in diets:
                queryset = queryset.filter(diet_tags__contains=[diet])
    if allergens:
        if connection.vendor == "postgresql":
            queryset = queryset.exclude(allergens__overlap=allergens)
        else:
            for allergen in allergens:
                queryset = queryset.exclude(allergens__contains=[allergen])
    if price_min:
        try:
            queryset = queryset.filter(price__gte=Decimal(price_min))
        except Exception:  # pragma: no cover - validated upstream
            pass
    if price_max:
        try:
            queryset = queryset.filter(price__lte=Decimal(price_max))
        except Exception:  # pragma: no cover
            pass
    if cook_time_max:
        try:
            queryset = queryset.filter(cook_time_minutes__lte=int(cook_time_max))
        except ValueError:  # pragma: no cover
            pass
    if sort == "popular":
        queryset = queryset.order_by("-purchases_count", "-rating")
    elif sort == "rating":
        queryset = queryset.order_by("-rating", "-rating_count")
    else:
        queryset = queryset.order_by("-created_at")
    return queryset


def filter_deals(queryset: QuerySet[DealOffer], params: dict[str, str]) -> QuerySet[DealOffer]:
    city = params.get("city")
    network = params.get("network")
    is_online = params.get("is_online")
    sort = params.get("sort")

    if city:
        queryset = queryset.filter(city__iexact=city)
    if network:
        queryset = queryset.filter(network__icontains=network)
    if is_online in {"1", "true", "True"}:
        queryset = queryset.filter(is_online=True)
    elif is_online in {"0", "false", "False"}:
        queryset = queryset.filter(is_online=False)

    if sort == "discount":
        queryset = queryset.order_by("-discount_percent")
    elif sort == "price":
        queryset = queryset.order_by("price_after")
    else:
        queryset = queryset.order_by("-valid_until")
    return queryset