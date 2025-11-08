from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from django.db import transaction

from ..models import MealPlan, MealPlanItem


NutritionTotals = dict[str, float]


def _ensure_number(value: object) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 0.0
    return 0.0


def _normalize_nutrition_payload(raw: object) -> NutritionTotals:
    if isinstance(raw, dict):
        source = raw
    else:
        source = {}
    calories = _ensure_number(source.get("calories")) or 0.0
    protein = _ensure_number(source.get("protein")) or 0.0
    fat = _ensure_number(source.get("fat")) or 0.0
    carbs = _ensure_number(source.get("carbs")) or 0.0
    if "protein_g" in source:
        protein = _ensure_number(source.get("protein_g")) or protein
    if "fat_g" in source:
        fat = _ensure_number(source.get("fat_g")) or fat
    if "carbs_g" in source:
        carbs = _ensure_number(source.get("carbs_g")) or carbs
    return {
        "calories": calories,
        "protein_g": protein,
        "fat_g": fat,
        "carbs_g": carbs,
    }


def empty_nutrition() -> NutritionTotals:
    return {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}


def add_nutrition(lhs: NutritionTotals, rhs: NutritionTotals) -> NutritionTotals:
    return {
        "calories": lhs.get("calories", 0.0) + rhs.get("calories", 0.0),
        "protein_g": lhs.get("protein_g", 0.0) + rhs.get("protein_g", 0.0),
        "fat_g": lhs.get("fat_g", 0.0) + rhs.get("fat_g", 0.0),
        "carbs_g": lhs.get("carbs_g", 0.0) + rhs.get("carbs_g", 0.0),
    }


def format_nutrition(payload: NutritionTotals) -> NutritionTotals:
    return {
        "calories": round(payload.get("calories", 0.0), 2),
        "protein_g": round(payload.get("protein_g", 0.0), 2),
        "fat_g": round(payload.get("fat_g", 0.0), 2),
        "carbs_g": round(payload.get("carbs_g", 0.0), 2),
    }


def recipe_nutrition(recipe) -> NutritionTotals:
    metadata = recipe.metadata or {}
    nutrition = metadata.get("nutrition") if isinstance(metadata, dict) else {}
    return _normalize_nutrition_payload(nutrition)


def product_nutrition(product) -> NutritionTotals:
    nutrition = product.nutrition or {}
    return _normalize_nutrition_payload(nutrition)


def item_base_nutrition(item: MealPlanItem) -> NutritionTotals:
    if item.recipe:
        return recipe_nutrition(item.recipe)
    if item.product:
        return product_nutrition(item.product)
    return empty_nutrition()


def item_total_nutrition(item: MealPlanItem) -> NutritionTotals:
    base = item_base_nutrition(item)
    servings = float(item.servings or 0)
    return {
        "calories": base["calories"] * servings,
        "protein_g": base["protein_g"] * servings,
        "fat_g": base["fat_g"] * servings,
        "carbs_g": base["carbs_g"] * servings,
    }


@dataclass
class PlanNutritionAggregate:
    totals: NutritionTotals
    daily: dict[str, NutritionTotals]


def aggregate_plan_nutrition(plan: MealPlan, items: Iterable[MealPlanItem] | None = None) -> PlanNutritionAggregate:
    if items is None:
        items = plan.items.all()
    totals = empty_nutrition()
    daily_totals: dict[str, NutritionTotals] = defaultdict(empty_nutrition)
    for item in items:
        item_total = item_total_nutrition(item)
        totals = add_nutrition(totals, item_total)
        key = item.scheduled_for.isoformat() if item.scheduled_for else "unscheduled"
        daily_totals[key] = add_nutrition(daily_totals[key], item_total)
    return PlanNutritionAggregate(totals=totals, daily=dict(daily_totals))


def calculate_plan_stats(plan: MealPlan, items: Iterable[MealPlanItem] | None = None) -> dict[str, int | None]:
    aggregate = aggregate_plan_nutrition(plan, items)
    total_calories = int(round(aggregate.totals.get("calories", 0.0))) if aggregate.totals else 0
    duration_days: int | None = None
    if plan.start_date and plan.end_date and plan.end_date >= plan.start_date:
        duration_days = (plan.end_date - plan.start_date).days + 1
    calories_per_day: int | None = None
    if duration_days and duration_days > 0:
        calories_per_day = int(round(total_calories / duration_days)) if total_calories else 0
    return {
        "duration_days": duration_days,
        "total_calories": total_calories,
        "calories_per_day": calories_per_day,
    }


def sync_plan_stats(plan: MealPlan, items: Iterable[MealPlanItem] | None = None) -> None:
    stats = calculate_plan_stats(plan, items)
    fields: list[str] = []
    for field, value in stats.items():
        setattr(plan, field, value)
        fields.append(field)
    if not fields:
        return
    with transaction.atomic():
        plan.__class__.objects.filter(pk=plan.pk).update(**{field: getattr(plan, field) for field in fields})


__all__ = [
    "PlanNutritionAggregate",
    "add_nutrition",
    "aggregate_plan_nutrition",
    "calculate_plan_stats",
    "empty_nutrition",
    "format_nutrition",
    "item_base_nutrition",
    "item_total_nutrition",
    "product_nutrition",
    "recipe_nutrition",
    "sync_plan_stats",
]
