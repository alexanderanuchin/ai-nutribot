"""Marketplace constants shared across services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from apps.market.models import Product, Recipe, Store

MarketResource = Literal["recipes", "products", "stores"]


@dataclass(frozen=True)
class QuickFilter:
    """Represents a quick filter chip exposed by search suggestions."""

    id: str
    label: str
    param: str
    value: str | int | bool
    resource: MarketResource


MARKET_QUICK_FILTERS: dict[MarketResource, tuple[QuickFilter, ...]] = {
    "recipes": (
        QuickFilter(id="fast", label="До 30 мин", param="max_time", value=30, resource="recipes"),
        QuickFilter(id="high-protein", label="Больше белка", param="min_protein", value=25, resource="recipes"),
        QuickFilter(id="budget", label="До 300 ₽", param="max_price", value=300, resource="recipes"),
        QuickFilter(id="plant-based", label="Растительные", param="tag", value="plant-based", resource="recipes"),
    ),
    "products": (
        QuickFilter(id="organic", label="Органика", param="tag", value="organic", resource="products"),
        QuickFilter(id="discount", label="Со скидкой", param="discount_only", value=True, resource="products"),
        QuickFilter(id="in-stock", label="В наличии", param="available", value=True, resource="products"),
        QuickFilter(id="local", label="Локальные", param="origin", value="local", resource="products"),
    ),
    "stores": (
        QuickFilter(id="express", label="Экспресс", param="max_eta", value=45, resource="stores"),
        QuickFilter(id="free-delivery", label="Бесплатная доставка", param="free_delivery", value=True, resource="stores"),
        QuickFilter(id="online", label="Онлайн", param="is_online", value=True, resource="stores"),
        QuickFilter(id="premium", label="Премиум", param="tag", value="premium", resource="stores"),
    ),
}


MARKET_RESOURCE_MODELS: dict[MarketResource, type[Recipe | Product | Store]] = {
    "recipes": Recipe,
    "products": Product,
    "stores": Store,
}

