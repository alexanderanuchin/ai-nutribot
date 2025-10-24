from __future__ import annotations

import logging
from decimal import Decimal

from django.db import IntegrityError, models, transaction

from nutribot.middleware import get_request_id

from ..models import Recipe, RecipePurchase

logger = logging.getLogger("feed.marketplace")


def publish_recipe(recipe: Recipe, *, request=None) -> Recipe:
    rid = getattr(request, "request_id", get_request_id())
    if recipe.status == Recipe.Status.PUBLISHED:
        return recipe
    recipe.status = Recipe.Status.PUBLISHED
    recipe.save(update_fields=["status", "updated_at"])
    logger.info(
        "recipe published",
        extra={"rid": rid, "recipe_id": recipe.id, "author_id": recipe.author_id},
    )
    return recipe


def create_purchase(*, user, recipe: Recipe, amount: Decimal | None = None, request=None) -> RecipePurchase:
    rid = getattr(request, "request_id", get_request_id())
    if recipe.status != Recipe.Status.PUBLISHED:
        raise ValueError("Recipe is not available for purchase")
    if not recipe.is_premium:
        raise ValueError("Recipe does not contain premium content")
    purchase_amount = amount or recipe.price
    if purchase_amount <= 0:
        raise ValueError("Purchase amount must be positive")
    try:
        with transaction.atomic():
            purchase, created = RecipePurchase.objects.get_or_create(
                user=user,
                recipe=recipe,
                defaults={
                    "amount": purchase_amount,
                    "currency": recipe.currency,
                    "status": RecipePurchase.Status.COMPLETED,
                    "provider": "test",
                },
            )
            if created:
                Recipe.objects.filter(pk=recipe.pk).update(
                    purchases_count=models.F("purchases_count") + 1
                )
    except IntegrityError as exc:  # pragma: no cover - defensive double submit
        logger.warning(
            "purchase creation failed",
            extra={
                "rid": rid,
                "recipe_id": recipe.id,
                "user_id": user.id,
                "error": str(exc),
            },
        )
        raise
    else:
        logger.info(
            "recipe purchased",
            extra={
                "rid": rid,
                "recipe_id": recipe.id,
                "user_id": user.id,
                "amount": float(purchase.amount),
            },
        )
    return purchase