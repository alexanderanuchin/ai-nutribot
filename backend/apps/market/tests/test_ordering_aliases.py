from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market.models import Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_store_ordering_aliases(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="market-visitor", password="secret123")
    api_client.force_authenticate(user=user)

    slow = Store.objects.create(
        owner=user,
        name="Slow & Steady",
        slug="slow-and-steady",
        description="",
        city="Москва",
        metadata={"rating": 4.1, "delivery_eta_minutes": 75},
        is_active=True,
    )
    fast = Store.objects.create(
        owner=user,
        name="Fast Fellows",
        slug="fast-fellows",
        description="",
        city="Москва",
        metadata={"rating": 4.9, "delivery_eta_minutes": 30},
        is_active=True,
    )
    medium = Store.objects.create(
        owner=user,
        name="Medium Market",
        slug="medium-market",
        description="",
        city="Москва",
        metadata={"rating": 4.5, "delivery_eta_minutes": 55},
        is_active=True,
    )

    response = api_client.get(
        reverse("market:market-store-list"),
        {"ordering": "-rating"},
    )
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["results"]]
    assert slugs[:3] == [fast.slug, medium.slug, slow.slug]

    response = api_client.get(
        reverse("market:market-store-list"),
        {"ordering": "eta"},
    )
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["results"]]
    assert slugs[:3] == [fast.slug, medium.slug, slow.slug]

    error_response = api_client.get(
        reverse("market:market-store-list"),
        {"ordering": "__hacker"},
    )
    assert error_response.status_code == 400
    assert "__hacker" in "".join(error_response.json().get("ordering", []))


@pytest.mark.django_db
def test_product_discount_ordering_alias(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="market-operator", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Discount Depot",
        slug="discount-depot",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )

    high_discount = Product.objects.create(
        store=store,
        title="High Discount", slug="high-discount", description="",
        price=Decimal("400.00"), currency="RUB", weight_grams=100,
        tags=[], nutrition={}, metadata={"rating": 4.8, "discount_percent": 35},
        is_published=True,
    )
    low_discount = Product.objects.create(
        store=store,
        title="Low Discount", slug="low-discount", description="",
        price=Decimal("250.00"), currency="RUB", weight_grams=100,
        tags=[], nutrition={}, metadata={"rating": 4.6, "discount_percent": 10},
        is_published=True,
    )
    Product.objects.create(
        store=store,
        title="No Discount", slug="no-discount", description="",
        price=Decimal("150.00"), currency="RUB", weight_grams=100,
        tags=[], nutrition={}, metadata={"rating": 3.5, "discount_percent": 0},
        is_published=True,
    )

    response = api_client.get(
        reverse("market:market-product-list"),
        {"ordering": "-discount", "min_rating": 4},
    )
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["results"]]
    assert slugs[:2] == [high_discount.slug, low_discount.slug]


@pytest.mark.django_db
def test_recipe_calories_ordering_alias(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="chef-ordering", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Kitchen Lab",
        slug="kitchen-lab",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )

    lighter = Recipe.objects.create(
        store=store,
        title="Lighter Bowl",
        slug="lighter-bowl",
        summary="",
        cooking_time_minutes=20,
        servings=2,
        difficulty="easy",
        is_public=True,
        metadata={
            "rating": 4.7,
            "nutrition": {"calories": 320, "protein_g": 26},
            "price": 260,
        },
    )
    heavier = Recipe.objects.create(
        store=store,
        title="Hearty Bowl",
        slug="hearty-bowl",
        summary="",
        cooking_time_minutes=35,
        servings=3,
        difficulty="medium",
        is_public=True,
        metadata={
            "rating": 4.5,
            "nutrition": {"calories": 480, "protein_g": 32},
            "price": {"value": 340, "currency": "RUB"},
        },
    )

    response = api_client.get(
        reverse("market:market-recipe-list"),
        {"ordering": "calories", "min_protein": 20, "max_price": 400},
    )
    assert response.status_code == 200
    payload = response.json()
    slugs = [item["slug"] for item in payload["results"]]
    assert slugs[:2] == [lighter.slug, heavier.slug]
