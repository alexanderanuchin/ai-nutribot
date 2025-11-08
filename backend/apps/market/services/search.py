"""Search orchestration for /market resources."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from django.db import models
from django.db.models import Prefetch, Q

from apps.market.constants import MARKET_QUICK_FILTERS, MarketResource
from apps.market.filters import coerce_decimal, coerce_int
from apps.market.models import Inventory, Product, Recipe, RecipeIngredient, Store
from apps.market.services.premium import get_recipe_price_stars, is_recipe_premium


SearchResource = MarketResource | Literal["all"]


@dataclass(slots=True)
class MarketSearchResult:
    resource: MarketResource
    id: int
    title: str
    subtitle: str | None
    description: str | None
    tags: list[str]
    metrics: dict[str, Any]
    preview: dict[str, Any]


@dataclass(slots=True)
class MarketSearchPayload:
    results: list[MarketSearchResult]
    total: int
    facets: dict[str, list[dict[str, Any]]]
    suggestions: dict[str, Any]


class MarketSearchService:
    """Performs multi-resource discovery for the marketplace."""

    def __init__(
        self,
        *,
        user,
        query: str,
        resource: SearchResource,
        limit: int = 12,
        filters: dict[str, Any] | None = None,
    ) -> None:
        self.user = user
        self.query = query.strip()
        self.resource = resource
        self.limit = max(1, min(limit, 30))
        self.filters = filters or {}

    def execute(self) -> MarketSearchPayload:
        buckets: list[tuple[MarketResource, Iterable[MarketSearchResult], int, dict[str, list[dict[str, Any]]]]] = []
        facets: dict[str, list[dict[str, Any]]] = {}
        suggestions: dict[str, Any] = {
            "quick_filters": self._collect_quick_filters(),
            "popular": [],
            "recent": [],
        }

        resources = (
            [self.resource]
            if self.resource in {"recipes", "products", "stores"}
            else ["recipes", "products", "stores"]
        )
        budget_per_bucket = max(1, self.limit // len(resources))

        total = 0
        for idx, bucket in enumerate(resources):
            bucket_limit = budget_per_bucket
            if idx == len(resources) - 1:
                bucket_limit = self.limit - total
            if bucket_limit <= 0:
                continue
            bucket_results, bucket_total, bucket_facets = self._search_bucket(bucket, bucket_limit)
            buckets.append((bucket, bucket_results, bucket_total, bucket_facets))
            facets[bucket] = bucket_facets.get(bucket, [])
            total += bucket_total

        results: list[MarketSearchResult] = []
        popular_candidates: Counter[str] = Counter()
        for resource_id, bucket_results, bucket_total, bucket_facets in buckets:
            results.extend(bucket_results)
            for facet_group in bucket_facets.values():
                for facet in facet_group:
                    value = facet.get("value")
                    if isinstance(value, str):
                        popular_candidates[value.lower()] += facet.get("count", 0)

        suggestions["popular"] = [value for value, _ in popular_candidates.most_common(6)]

        return MarketSearchPayload(results=results, total=total, facets=facets, suggestions=suggestions)

    def _collect_quick_filters(self) -> list[dict[str, Any]]:
        if self.resource in {"recipes", "products", "stores"}:
            filters = MARKET_QUICK_FILTERS[self.resource]
        else:
            filters = tuple(filter for values in MARKET_QUICK_FILTERS.values() for filter in values)
        return [
            {
                "id": quick_filter.id,
                "label": quick_filter.label,
                "param": quick_filter.param,
                "value": quick_filter.value,
                "resource": quick_filter.resource,
            }
            for quick_filter in filters
        ]

    def _search_bucket(
        self,
        resource: MarketResource,
        limit: int,
    ) -> tuple[list[MarketSearchResult], int, dict[str, list[dict[str, Any]]]]:
        if resource == "recipes":
            return self._search_recipes(limit)
        if resource == "products":
            return self._search_products(limit)
        return self._search_stores(limit)

    def _search_recipes(
        self,
        limit: int,
    ) -> tuple[list[MarketSearchResult], int, dict[str, list[dict[str, Any]]]]:
        qs = Recipe.objects.select_related("store", "author").filter(is_public=True, store__is_active=True)
        if self.query:
            qs = qs.filter(
                Q(title__icontains=self.query)
                | Q(summary__icontains=self.query)
                | Q(metadata__category__icontains=self.query)
                | Q(metadata__diet__icontains=self.query)
            )
        max_time = coerce_int(self.filters.get("max_time"))
        if max_time is not None:
            qs = qs.filter(cooking_time_minutes__lte=max_time)
        difficulty = self.filters.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty__iexact=str(difficulty))
        tag = self.filters.get("tag")
        if tag:
            qs = qs.filter(metadata__tags__icontains=str(tag))
        min_rating = coerce_decimal(self.filters.get("min_rating"))
        if min_rating is not None:
            qs = qs.filter(metadata__rating__gte=float(min_rating))
        min_protein = coerce_decimal(self.filters.get("min_protein"))
        if min_protein is not None:
            qs = qs.filter(metadata__nutrition__protein_g__gte=float(min_protein))
        max_price = coerce_decimal(self.filters.get("max_price"))
        if max_price is not None:
            qs = qs.filter(
                Q(metadata__price__value__lte=float(max_price))
                | Q(metadata__price__lte=float(max_price))
            )
        qs = qs.order_by("-published_at", "-id")

        total = qs.count()
        recipes = list(qs[:limit])

        tags_counter: Counter[str] = Counter()
        difficulty_counter: Counter[str] = Counter()
        for recipe in recipes:
            tags = recipe.metadata.get("tags") if isinstance(recipe.metadata, dict) else None
            if isinstance(tags, list):
                tags_counter.update(tag for tag in tags if isinstance(tag, str))
            if recipe.difficulty:
                difficulty_counter[recipe.difficulty.lower()] += 1

        facets = {
            "recipes": [
                {"id": f"difficulty:{name}", "label": name.title(), "value": name, "count": count}
                for name, count in difficulty_counter.most_common()
            ]
            + [
                {"id": f"tag:{name}", "label": name.title(), "value": name, "count": count}
                for name, count in tags_counter.most_common(6)
            ]
        }

        results = [self._map_recipe(recipe) for recipe in recipes]
        return results, total, facets

    def _map_recipe(self, recipe: Recipe) -> MarketSearchResult:
        metadata = recipe.metadata if isinstance(recipe.metadata, dict) else {}
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
        if not tags and metadata.get("category"):
            tags = [metadata["category"]]
        preview = {
            "image_url": metadata.get("hero_image_url") or metadata.get("preview_image_url"),
            "store": recipe.store.name,
        }
        metrics = {
            "cook_time_minutes": recipe.cooking_time_minutes,
            "servings": recipe.servings,
            "difficulty": recipe.difficulty or None,
            "is_premium": is_recipe_premium(recipe),
        }
        stars = get_recipe_price_stars(recipe)
        if stars is not None:
            metrics["price_stars"] = int(stars)
            metrics["currency"] = "STARS"
        return MarketSearchResult(
            resource="recipes",
            id=recipe.id,
            title=recipe.title,
            subtitle=metadata.get("headline") or None,
            description=recipe.summary or None,
            tags=[tag for tag in tags if isinstance(tag, str)],
            metrics=metrics,
            preview=preview,
        )

    def _search_products(
        self,
        limit: int,
    ) -> tuple[list[MarketSearchResult], int, dict[str, list[dict[str, Any]]]]:
        qs = (
            Product.objects.select_related("store", "inventory")
            .filter(is_published=True, store__is_active=True)
            .prefetch_related(Prefetch("ingredient_usages", queryset=RecipeIngredient.objects.only("id")))
        )
        if self.query:
            qs = qs.filter(Q(title__icontains=self.query) | Q(tags__icontains=self.query) | Q(description__icontains=self.query))

        min_price = coerce_decimal(self.filters.get("min_price"))
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        max_price = coerce_decimal(self.filters.get("max_price"))
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        tag = self.filters.get("tag")
        if tag:
            qs = qs.filter(tags__icontains=str(tag))
        if self.filters.get("available"):
            qs = qs.filter(inventory__quantity__gt=models.F("inventory__reserved"))
        brand = self.filters.get("brand")
        if brand:
            qs = qs.filter(metadata__brand__icontains=str(brand))
        if self.filters.get("discount_only"):
            qs = qs.filter(metadata__discount_percent__gt=0)
        min_rating = coerce_decimal(self.filters.get("min_rating"))
        if min_rating is not None:
            qs = qs.filter(metadata__rating__gte=float(min_rating))

        qs = qs.order_by("title", "id")
        total = qs.count()
        products = list(qs[:limit])

        tag_counter: Counter[str] = Counter()
        brand_counter: Counter[str] = Counter()
        for product in products:
            if isinstance(product.tags, list):
                tag_counter.update(tag for tag in product.tags if isinstance(tag, str))
            metadata = product.metadata if isinstance(getattr(product, "metadata", {}), dict) else {}
            brand_value = metadata.get("brand")
            if isinstance(brand_value, str):
                brand_counter[brand_value.lower()] += 1

        facets = {
            "products": [
                {"id": f"tag:{name}", "label": name.title(), "value": name, "count": count}
                for name, count in tag_counter.most_common(6)
            ]
        }

        results = [self._map_product(product) for product in products]
        return results, total, facets

    def _map_product(self, product: Product) -> MarketSearchResult:
        metadata = product.metadata if hasattr(product, "metadata") and isinstance(product.metadata, dict) else {}
        preview = {
            "image_url": metadata.get("image_url"),
            "store": product.store.name,
        }
        tags = product.tags if isinstance(product.tags, list) else []
        available = False
        if hasattr(product, "inventory") and isinstance(product.inventory, Inventory):
            available = product.inventory.quantity > product.inventory.reserved
        metrics = {
            "price": float(product.price),
            "currency": product.currency,
            "available": available,
        }
        return MarketSearchResult(
            resource="products",
            id=product.id,
            title=product.title,
            subtitle=metadata.get("subtitle"),
            description=product.description or None,
            tags=[tag for tag in tags if isinstance(tag, str)],
            metrics=metrics,
            preview=preview,
        )

    def _search_stores(
        self,
        limit: int,
    ) -> tuple[list[MarketSearchResult], int, dict[str, list[dict[str, Any]]]]:
        qs = Store.objects.filter(is_active=True)
        if self.query:
            qs = qs.filter(Q(name__icontains=self.query) | Q(description__icontains=self.query) | Q(city__icontains=self.query))
        city = self.filters.get("city")
        if city:
            qs = qs.filter(city__iexact=str(city))
        tag = self.filters.get("tag")
        if tag:
            qs = qs.filter(metadata__tags__icontains=str(tag))
        if self.filters.get("is_online"):
            qs = qs.filter(metadata__is_online=True)
        max_eta = coerce_int(self.filters.get("max_eta"))
        if max_eta is not None:
            qs = qs.filter(metadata__delivery_eta_minutes__lte=max_eta)
        min_rating = coerce_decimal(self.filters.get("min_rating"))
        if min_rating is not None:
            qs = qs.filter(metadata__rating__gte=float(min_rating))

        qs = qs.order_by("name", "id")
        total = qs.count()
        stores = list(qs[:limit])

        tags_counter: Counter[str] = Counter()
        city_counter: Counter[str] = Counter()
        for store in stores:
            metadata = store.metadata if isinstance(store.metadata, dict) else {}
            if metadata.get("tags") and isinstance(metadata["tags"], list):
                tags_counter.update(tag for tag in metadata["tags"] if isinstance(tag, str))
            if store.city:
                city_counter[store.city] += 1

        facets = {
            "stores": [
                {"id": f"city:{city}", "label": city, "value": city, "count": count}
                for city, count in city_counter.most_common(6)
            ]
            + [
                {"id": f"tag:{tag}", "label": tag.title(), "value": tag, "count": count}
                for tag, count in tags_counter.most_common(6)
            ]
        }

        results = [self._map_store(store) for store in stores]
        return results, total, facets

    def _map_store(self, store: Store) -> MarketSearchResult:
        metadata = store.metadata if isinstance(store.metadata, dict) else {}
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
        metrics = {
            "city": store.city,
            "delivery_eta_minutes": metadata.get("delivery_eta_minutes"),
            "delivery_price": metadata.get("delivery_price"),
        }
        preview = {
            "image_url": metadata.get("hero_image_url"),
            "logo_url": store.logo_url,
        }
        return MarketSearchResult(
            resource="stores",
            id=store.id,
            title=store.name,
            subtitle=metadata.get("headline") or None,
            description=store.description or None,
            tags=[tag for tag in tags if isinstance(tag, str)],
            metrics=metrics,
            preview=preview,
        )

