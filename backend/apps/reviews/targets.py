from __future__ import annotations

from typing import Type

from django.db import models

from apps.market.models import MealPlan, Product, Recipe, Store

_TARGET_ALIASES: dict[str, Type[models.Model]] = {
    "store": Store,
    "stores": Store,
    "product": Product,
    "products": Product,
    "recipe": Recipe,
    "recipes": Recipe,
    "plan": MealPlan,
    "plans": MealPlan,
    "meal_plan": MealPlan,
    "mealplan": MealPlan,
}


def resolve_target_model(alias: str) -> Type[models.Model]:
    normalized = alias.lower().strip()
    try:
        return _TARGET_ALIASES[normalized]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported target type: {alias}") from exc
