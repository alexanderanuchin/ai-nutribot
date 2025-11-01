#!/usr/bin/env python
"""Ad-hoc benchmark for market viewsets.

The script seeds a minimal dataset (idempotent) and measures ORM
performance for the most frequently accessed market viewsets.
"""
from __future__ import annotations

import os
import random
import statistics
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Sequence

# Force SQLite for repeatable local runs unless caller overrides
os.environ.setdefault("USE_SQLITE", "1")
BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutribot.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.test.client import RequestFactory
from django.test.utils import CaptureQueriesContext
from rest_framework.request import Request

from apps.market.models import (
    Cart,
    CartItem,
    Inventory,
    MealPlan,
    MealPlanItem,
    Product,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    Store,
)
from apps.market.roles import MODERATOR_GROUP_NAME, VENDOR_GROUP_NAME
from apps.market.views import CartViewSet, ProductViewSet, RecipeViewSet, StoreViewSet


User = get_user_model()
rf = RequestFactory()


def _ensure_groups() -> None:
    for name in (VENDOR_GROUP_NAME, MODERATOR_GROUP_NAME):
        Group.objects.get_or_create(name=name)


def seed_if_required() -> tuple[User, User]:
    _ensure_groups()
    operator, _ = User.objects.get_or_create(
        username="market-operator",
        defaults={"email": "operator@example.com"},
    )
    customer, _ = User.objects.get_or_create(
        username="market-customer",
        defaults={"email": "customer@example.com"},
    )

    if not operator.groups.filter(name=VENDOR_GROUP_NAME).exists():
        operator.groups.add(Group.objects.get(name=VENDOR_GROUP_NAME))

    if Store.objects.filter(slug="perf-store-1").exists():
        return operator, customer

    print("Seeding demo marketplace dataset ...")
    with transaction.atomic():
        stores: list[Store] = []
        for idx in range(1, 6):
            store = Store.objects.create(
                owner=operator,
                name=f"Performance Store {idx}",
                slug=f"perf-store-{idx}",
                city="Benchmark City" if idx % 2 else "Testopolis",
                is_active=True,
                metadata={
                    "rating": random.uniform(3.5, 4.9),
                    "delivery_eta_minutes": random.randint(25, 50),
                    "tags": ["organic", "local", "vegan" if idx % 2 else "protein"],
                },
            )
            stores.append(store)

        products: list[Product] = []
        for store in stores:
            for pidx in range(1, 51):
                product = Product.objects.create(
                    store=store,
                    title=f"Product {store.id}-{pidx}",
                    slug=f"product-{store.id}-{pidx}",
                    price=Decimal("10.0") + Decimal(pidx),
                    currency="RUB",
                    is_published=True,
                    metadata={
                        "discount_percent": pidx % 5,
                        "rating": random.uniform(3.0, 5.0),
                        "origin": "RU" if pidx % 2 else "US",
                        "tags": ["protein", "vegan", "snack"],
                    },
                )
                Inventory.objects.create(
                    product=product,
                    quantity=100 + pidx,
                    reserved=10,
                    reorder_threshold=5,
                )
                products.append(product)

        for store in stores:
            for ridx in range(1, 21):
                recipe = Recipe.objects.create(
                    store=store,
                    author=operator,
                    title=f"Recipe {store.id}-{ridx}",
                    slug=f"recipe-{store.id}-{ridx}",
                    cooking_time_minutes=15 + ridx,
                    servings=2,
                    difficulty="medium" if ridx % 2 else "easy",
                    is_public=True,
                    metadata={
                        "nutrition": {
                            "calories": 250 + ridx,
                            "protein_g": 15 + ridx,
                            "fat_g": 10 + ridx,
                            "carbs_g": 30 + ridx,
                        },
                        "price": {"value": 150 + ridx, "currency": "RUB"},
                        "rating": random.uniform(3.0, 5.0),
                        "tags": ["quick", "dinner", "vegan" if ridx % 2 else "protein"],
                    },
                )
                for step_order in range(1, 4):
                    RecipeStep.objects.create(
                        recipe=recipe,
                        order=step_order,
                        title=f"Step {step_order}",
                        instructions="Stir and cook",
                    )
                for ingredient_order in range(3):
                    ingredient_product = random.choice(products)
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        product=ingredient_product,
                        name=f"Ingredient {ingredient_product.slug}",
                        quantity=Decimal("1.0") + ingredient_order,
                        unit="pcs",
                    )

        cart, _ = Cart.objects.get_or_create(
            user=customer,
            store=stores[0],
            defaults={"status": Cart.Status.ACTIVE, "currency": "RUB"},
        )
        CartItem.objects.all().filter(cart=cart).delete()
        for product in products[:10]:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=2,
                price_snapshot=product.price,
            )

        plan, _ = MealPlan.objects.get_or_create(
            user=customer,
            title="Weekly plan",
            defaults={
                "description": "Benchmark plan",
                "start_date": date.today(),
            },
        )
        MealPlanItem.objects.filter(meal_plan=plan).delete()
        for day in range(5):
            MealPlanItem.objects.create(
                meal_plan=plan,
                recipe=random.choice(Recipe.objects.all()),
                servings=Decimal("1.0"),
            )

    return operator, customer


@dataclass
class BenchmarkResult:
    label: str
    duration_ms: float
    queries: int
    count: int


def run_benchmark(operator: User, customer: User) -> Sequence[BenchmarkResult]:
    results: list[BenchmarkResult] = []

    def record(label: str, func: Callable[[], Iterable]):
        with CaptureQueriesContext(connection) as ctx:
            start = time.perf_counter()
            data = list(func())
            duration_ms = (time.perf_counter() - start) * 1000
        results.append(
            BenchmarkResult(label=label, duration_ms=duration_ms, queries=len(ctx), count=len(data))
        )

    # Stores listing for authenticated customer with city filter
    store_request = rf.get("/api/market/stores/", {"city": "Benchmark City"})
    store_request.user = customer
    drf_store_request = Request(store_request)
    drf_store_request.user = customer
    store_view = StoreViewSet()
    store_view.request = drf_store_request
    store_view.action = "list"
    record("store-list", lambda: store_view.get_queryset()[:50])

    # Products listing filtered by price window
    product_request = rf.get(
        "/api/market/products/",
        {"min_price": "20", "max_price": "70", "store": "perf-store-1"},
    )
    product_request.user = customer
    drf_product_request = Request(product_request)
    drf_product_request.user = customer
    product_view = ProductViewSet()
    product_view.request = drf_product_request
    product_view.action = "list"
    record("product-list", lambda: product_view.get_queryset()[:50])

    # Recipes listing with time filter
    recipe_request = rf.get("/api/market/recipes/", {"max_time": "40"})
    recipe_request.user = customer
    drf_recipe_request = Request(recipe_request)
    drf_recipe_request.user = customer
    recipe_view = RecipeViewSet()
    recipe_view.request = drf_recipe_request
    recipe_view.action = "list"
    record("recipe-list", lambda: recipe_view.get_queryset()[:50])

    # Cart listing for customer
    cart_request = rf.get("/api/market/carts/")
    cart_request.user = customer
    drf_cart_request = Request(cart_request)
    drf_cart_request.user = customer
    cart_view = CartViewSet()
    cart_view.request = drf_cart_request
    cart_view.action = "list"
    record("cart-list", lambda: cart_view.get_queryset()[:20])

    return results


def main() -> int:
    operator, customer = seed_if_required()
    results = run_benchmark(operator, customer)

    print("\nSummary (duration ms / query count / result count):")
    for item in results:
        print(
            f"- {item.label}: {item.duration_ms:.2f} ms | {item.queries} queries | {item.count} rows"
        )

    if len(results) >= 2:
        durations = [item.duration_ms for item in results]
        print(
            f"\nMean duration: {statistics.mean(durations):.2f} ms, "
            f"median: {statistics.median(durations):.2f} ms"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
