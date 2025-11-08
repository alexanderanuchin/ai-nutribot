from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.market.models import MealPlan, MealPlanItem, Product, Recipe, Store

User = get_user_model()


@dataclass(slots=True)
class EligibilityResult:
    allowed: bool
    reason: str | None = None

    @property
    def is_allowed(self) -> bool:
        return self.allowed


def _bool_result(value: bool, reason: str | None = None) -> EligibilityResult:
    return EligibilityResult(allowed=value, reason=reason if not value else None)


def _extract_user_ids(candidate: object) -> Iterable[int]:
    if isinstance(candidate, list | tuple | set):
        for value in candidate:
            try:
                yield int(value)
            except (TypeError, ValueError):
                continue


def can_review_store(user: User, store: Store) -> EligibilityResult:
    if store.owner_id == user.id:
        return _bool_result(False, "Нельзя оценивать собственный магазин")
    has_plan_items = MealPlanItem.objects.filter(
        Q(product__store=store) | Q(recipe__store=store),
        meal_plan__user=user,
    ).exists()
    if has_plan_items:
        return _bool_result(True)
    return _bool_result(False, "Сначала попробуйте продукты или рецепты магазина")


def can_review_product(user: User, product: Product) -> EligibilityResult:
    has_plan_item = MealPlanItem.objects.filter(
        meal_plan__user=user,
        product=product,
    ).exists()
    if has_plan_item:
        return _bool_result(True)
    return _bool_result(False, "Добавьте продукт в план перед отзывом")


def can_review_recipe(user: User, recipe: Recipe) -> EligibilityResult:
    has_plan_item = MealPlanItem.objects.filter(
        meal_plan__user=user,
        recipe=recipe,
    ).exists()
    if has_plan_item:
        return _bool_result(True)
    return _bool_result(False, "Приготовьте рецепт или купите доступ")


def can_review_meal_plan(user: User, plan: MealPlan) -> EligibilityResult:
    if plan.user_id == user.id:
        return _bool_result(False, "Нельзя оценивать собственный план")
    metadata = plan.metadata or {}
    purchased_ids = metadata.get("purchased_user_ids") or []
    if any(user.id == candidate for candidate in _extract_user_ids(purchased_ids)):
        return _bool_result(True)
    return _bool_result(False, "План недоступен в вашей библиотеке")


def ensure_can_review(user: User, target: object) -> EligibilityResult:
    if isinstance(target, Store):
        return can_review_store(user, target)
    if isinstance(target, Product):
        return can_review_product(user, target)
    if isinstance(target, Recipe):
        return can_review_recipe(user, target)
    if isinstance(target, MealPlan):
        return can_review_meal_plan(user, target)
    return EligibilityResult(False, "Этот объект нельзя оценить")
