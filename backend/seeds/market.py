"""Development fixtures for marketplace module."""

from __future__ import annotations

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.market.models import (
    Cart,
    CartItem,
    MealPlan,
    MealPlanItem,
    Product,
    Inventory,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    Store,
)
from apps.market.roles import ensure_market_roles


def create():
    ensure_market_roles()
    User = get_user_model()

    vendor, _ = User.objects.get_or_create(
        username="demo-vendor",
        defaults={"email": "vendor@example.com"},
    )
    customer, _ = User.objects.get_or_create(
        username="demo-customer",
        defaults={"email": "customer@example.com"},
    )

    store, _ = Store.objects.get_or_create(
        slug="demo-store",
        defaults={
            "owner": vendor,
            "name": "Demo Market Store",
            "description": "Ремесленная лавка полезных продуктов",
            "city": "Москва",
            "logo_url": "https://placehold.co/128x128",
            "is_active": True,
            "is_verified": True,
        },
    )

    product, _ = Product.objects.get_or_create(
        store=store,
        slug="protein-granola",
        defaults={
            "title": "Протеиновая гранола",
            "description": "Хрустящая гранола без сахара с орехами и ягодами.",
            "price": Decimal("390.00"),
            "currency": "RUB",
            "weight_grams": 250,
            "tags": ["granola", "protein", "vegan"],
            "nutrition": {
                "calories": 320,
                "protein": 22,
                "fat": 9,
                "carbs": 35,
            },
            "is_published": True,
            "published_at": timezone.now(),
        },
    )
    Inventory.objects.update_or_create(
        product=product,
        defaults={"quantity": 120, "reserved": 5, "reorder_threshold": 20},
    )

    recipe, _ = Recipe.objects.get_or_create(
        store=store,
        slug="granola-breakfast",
        defaults={
            "author": vendor,
            "title": "Боул с гранолой",
            "summary": "Пяти минутный завтрак с высоким содержанием белка.",
            "cooking_time_minutes": 5,
            "servings": 1,
            "difficulty": "easy",
            "is_public": True,
            "published_at": timezone.now(),
            "metadata": {"category": "breakfast"},
        },
    )
    RecipeStep.objects.get_or_create(
        recipe=recipe,
        order=1,
        defaults={
            "title": "Смешайте ингредиенты",
            "instructions": "Смешайте гранолу с йогуртом и ягодами в миске.",
        },
    )
    RecipeIngredient.objects.get_or_create(
        recipe=recipe,
        product=product,
        defaults={
            "name": "Протеиновая гранола",
            "quantity": Decimal("60"),
            "unit": "г",
        },
    )

    cart, _ = Cart.objects.get_or_create(
        user=customer,
        store=store,
        status=Cart.Status.ACTIVE,
        defaults={"currency": "RUB"},
    )
    CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={
            "quantity": 2,
            "price_snapshot": product.price,
        },
    )

    meal_plan, _ = MealPlan.objects.get_or_create(
        user=customer,
        title="Неделя энергии",
        defaults={
            "description": "Пример плана питания с акцентом на быстрые завтраки.",
            "start_date": timezone.now().date(),
            "end_date": timezone.now().date() + timedelta(days=7),
            "is_published": True,
            "published_at": timezone.now(),
            "metadata": {"goal": "energy"},
        },
    )
    MealPlanItem.objects.get_or_create(
        meal_plan=meal_plan,
        scheduled_for=timezone.now().date(),
        meal_type="breakfast",
        recipe=recipe,
        defaults={
            "servings": Decimal("1.0"),
            "notes": "Добавьте сезонные ягоды.",
        },
    )

    print("Seeded demo marketplace data")


if __name__ == "__main__":  # pragma: no cover
    create()