"""Helpers for premium marketplace content access and purchases."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Tuple

from django.db import transaction

from nutribot.middleware import get_request_id

from apps.orders.models import WalletTransaction
from apps.orders.services.wallet import WalletInsufficientFunds, wallet_withdraw
from apps.users.models import Profile

from ..models import MealPlan, MealPlanAccess, Recipe, RecipeAccess

logger = logging.getLogger("audit.market.premium")


@dataclass(slots=True, frozen=True)
class PurchaseResult:
    access: RecipeAccess | MealPlanAccess
    wallet_transaction: WalletTransaction | None


def _resolve_rid(rid: str | None) -> str:
    return rid or get_request_id()


def _coerce_decimal(value: object) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None


def _normalize_stars_amount(value: Decimal) -> Decimal:
    quantized = value.quantize(Decimal("1"))
    return quantized if quantized >= 0 else Decimal("0")


def _recipe_metadata(recipe: Recipe) -> dict:
    metadata = recipe.metadata or {}
    return metadata if isinstance(metadata, dict) else {}


def _plan_metadata(plan: MealPlan) -> dict:
    metadata = plan.metadata or {}
    return metadata if isinstance(metadata, dict) else {}


def get_recipe_price_stars(recipe: Recipe) -> Optional[Decimal]:
    metadata = _recipe_metadata(recipe)
    raw_price = metadata.get("price")
    if isinstance(raw_price, dict):
        candidate = _coerce_decimal(raw_price.get("stars") or raw_price.get("value"))
    else:
        candidate = _coerce_decimal(raw_price)
    if candidate is None:
        return None
    normalized = _normalize_stars_amount(candidate)
    return normalized if normalized > 0 else None


def get_meal_plan_price_stars(plan: MealPlan) -> Optional[Decimal]:
    candidate = _coerce_decimal(plan.price_amount)
    if candidate is None:
        return None
    normalized = _normalize_stars_amount(candidate)
    return normalized if normalized > 0 else None


def is_recipe_premium(recipe: Recipe) -> bool:
    metadata = _recipe_metadata(recipe)
    if metadata.get("is_premium"):
        return True
    return get_recipe_price_stars(recipe) is not None


def has_recipe_access(profile: Profile, recipe: Recipe) -> bool:
    if not is_recipe_premium(recipe):
        return True
    if recipe.store.owner_id == profile.user_id or recipe.author_id == profile.user_id:
        return True
    prefetched = getattr(recipe, "_prefetched_accesses", None)
    if prefetched is not None:
        return any(access.profile_id == profile.id for access in prefetched)
    return RecipeAccess.objects.filter(profile=profile, recipe=recipe).exists()


def has_meal_plan_access(profile: Profile, plan: MealPlan) -> bool:
    if plan.user_id == profile.user_id:
        return True
    price = get_meal_plan_price_stars(plan)
    if price is None:
        return True
    prefetched = getattr(plan, "_prefetched_accesses", None)
    if prefetched is not None:
        return any(access.profile_id == profile.id for access in prefetched)
    return MealPlanAccess.objects.filter(profile=profile, meal_plan=plan).exists()


def _append_plan_purchase_marker(plan: MealPlan, profile: Profile) -> None:
    metadata = _plan_metadata(plan)
    purchased_ids: Iterable[int] = metadata.get("purchased_user_ids") or []
    seen = {int(value) for value in purchased_ids if isinstance(value, (int, str)) and str(value).isdigit()}
    if profile.user_id in seen:
        return
    updated = list(seen)
    updated.append(profile.user_id)
    metadata["purchased_user_ids"] = updated
    plan.metadata = metadata
    plan.save(update_fields=["metadata", "updated_at"])


def purchase_recipe(
    profile: Profile,
    recipe: Recipe,
    *,
    rid: str | None = None,
    idempotency_key: str | None = None,
) -> PurchaseResult:
    resolved_rid = _resolve_rid(rid)
    price = get_recipe_price_stars(recipe)
    defaults = {"metadata": {}}
    with transaction.atomic():
        access, created = RecipeAccess.objects.select_for_update().get_or_create(
            profile=profile,
            recipe=recipe,
            defaults=defaults,
        )
        if price is None:
            if created:
                logger.info(
                    "market.recipe.access.free",
                    extra={"rid": resolved_rid, "profile_id": profile.id, "recipe_id": recipe.id},
                )
            return PurchaseResult(access=access, wallet_transaction=None)
        if access.wallet_transaction_id:
            return PurchaseResult(access=access, wallet_transaction=access.wallet_transaction)
        description = f"Покупка рецепта «{recipe.title[:80]}»"
        metadata = {
            "content_type": "market.recipe",
            "recipe_id": recipe.id,
            "store_id": recipe.store_id,
            "profile_id": profile.id,
        }
        withdraw_key = idempotency_key or f"market:recipe:{recipe.id}:profile:{profile.id}"
        wallet_tx = wallet_withdraw(
            profile,
            currency=WalletTransaction.Currency.TELEGRAM_STARS,
            amount=price,
            description=description,
            metadata=metadata,
            idempotency_key=withdraw_key,
        )
        access.wallet_transaction = wallet_tx
        access.metadata = {**(access.metadata or {}), "price_stars": str(price)}
        access.save(update_fields=["wallet_transaction", "metadata", "updated_at"])
    logger.info(
        "market.recipe.purchased",
        extra={
            "rid": resolved_rid,
            "profile_id": profile.id,
            "recipe_id": recipe.id,
            "wallet_transaction_id": getattr(access, "wallet_transaction_id", None),
            "price_stars": str(price),
        },
    )
    return PurchaseResult(access=access, wallet_transaction=access.wallet_transaction)


def purchase_meal_plan(
    profile: Profile,
    plan: MealPlan,
    *,
    rid: str | None = None,
    idempotency_key: str | None = None,
) -> PurchaseResult:
    resolved_rid = _resolve_rid(rid)
    price = get_meal_plan_price_stars(plan)
    defaults = {"metadata": {}}
    with transaction.atomic():
        access, created = MealPlanAccess.objects.select_for_update().get_or_create(
            profile=profile,
            meal_plan=plan,
            defaults=defaults,
        )
        if price is None:
            if created:
                logger.info(
                    "market.meal_plan.access.free",
                    extra={"rid": resolved_rid, "profile_id": profile.id, "meal_plan_id": plan.id},
                )
            _append_plan_purchase_marker(plan, profile)
            return PurchaseResult(access=access, wallet_transaction=None)
        if access.wallet_transaction_id:
            _append_plan_purchase_marker(plan, profile)
            return PurchaseResult(access=access, wallet_transaction=access.wallet_transaction)
        description = f"Покупка плана питания «{plan.title[:80]}»"
        metadata = {
            "content_type": "market.meal_plan",
            "meal_plan_id": plan.id,
            "profile_id": profile.id,
        }
        withdraw_key = idempotency_key or f"market:mealplan:{plan.id}:profile:{profile.id}"
        wallet_tx = wallet_withdraw(
            profile,
            currency=WalletTransaction.Currency.TELEGRAM_STARS,
            amount=price,
            description=description,
            metadata=metadata,
            idempotency_key=withdraw_key,
        )
        access.wallet_transaction = wallet_tx
        access.metadata = {**(access.metadata or {}), "price_stars": str(price)}
        access.save(update_fields=["wallet_transaction", "metadata", "updated_at"])
        _append_plan_purchase_marker(plan, profile)
    logger.info(
        "market.meal_plan.purchased",
        extra={
            "rid": resolved_rid,
            "profile_id": profile.id,
            "meal_plan_id": plan.id,
            "wallet_transaction_id": getattr(access, "wallet_transaction_id", None),
            "price_stars": str(price),
        },
    )
    return PurchaseResult(access=access, wallet_transaction=access.wallet_transaction)


__all__ = [
    "PurchaseResult",
    "WalletInsufficientFunds",
    "get_recipe_price_stars",
    "get_meal_plan_price_stars",
    "has_recipe_access",
    "has_meal_plan_access",
    "is_recipe_premium",
    "purchase_recipe",
    "purchase_meal_plan",
]
