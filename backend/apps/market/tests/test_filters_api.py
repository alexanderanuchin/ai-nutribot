import pytest
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APIClient

from apps.market.models import Inventory, Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_product_list_supports_ordering_and_min_rating(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="vendor-order", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Ordering Store",
        slug="ordering-store",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )

    premium = Product.objects.create(
        store=store,
        title="Премиум батончик",
        slug="premium-bar",
        description="",
        price=Decimal("250.00"),
        currency="RUB",
        weight_grams=80,
        tags=["snack"],
        nutrition={},
        metadata={"rating": 4.8, "rating_count": 21},
        is_published=True,
    )
    standard = Product.objects.create(
        store=store,
        title="Стандартный батончик",
        slug="standard-bar",
        description="",
        price=Decimal("120.00"),
        currency="RUB",
        weight_grams=80,
        tags=["snack"],
        nutrition={},
        metadata={"rating": 4.2, "rating_count": 9},
        is_published=True,
    )
    Product.objects.create(
        store=store,
        title="Эконом батончик",
        slug="economy-bar",
        description="",
        price=Decimal("80.00"),
        currency="RUB",
        weight_grams=80,
        tags=["snack"],
        nutrition={},
        metadata={"rating": 3.0, "rating_count": 3},
        is_published=True,
    )

    Inventory.objects.create(product=premium, quantity=10, reserved=2)
    Inventory.objects.create(product=standard, quantity=8, reserved=1)

    response = api_client.get(
        reverse("market:market-product-list"),
        {"ordering": "-price", "min_rating": 4},
    )
    assert response.status_code == 200
    payload = response.json()
    prices = [Decimal(item["price"]) for item in payload["results"]]
    ids = [item["id"] for item in payload["results"]]
    assert len(payload["results"]) == 2
    assert prices == sorted(prices, reverse=True)
    assert ids[0] == premium.id
    assert ids[1] == standard.id


@pytest.mark.django_db
def test_recipe_list_supports_protein_and_price_filters(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="chef-filter", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Filter Kitchen",
        slug="filter-kitchen",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )

    qualifying = Recipe.objects.create(
        store=store,
        title="Белковый салат",
        slug="protein-salad",
        summary="",
        cooking_time_minutes=15,
        servings=2,
        difficulty="easy",
        is_public=True,
        metadata={
            "rating": 4.5,
            "nutrition": {"protein_g": 28, "calories": 420},
            "price": {"value": 290, "currency": "RUB"},
        },
    )
    Recipe.objects.create(
        store=store,
        title="Сладкий десерт",
        slug="sweet-dessert",
        summary="",
        cooking_time_minutes=30,
        servings=4,
        difficulty="medium",
        is_public=True,
        metadata={
            "rating": 4.2,
            "nutrition": {"protein_g": 9, "calories": 510},
            "price": {"value": 420, "currency": "RUB"},
        },
    )

    response = api_client.get(
        reverse("market:market-recipe-list"),
        {"min_protein": 20, "max_price": 300, "min_rating": 4},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == qualifying.id
