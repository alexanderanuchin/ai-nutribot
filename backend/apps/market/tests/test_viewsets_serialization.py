from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market.models import Inventory, Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_product_viewset_returns_flat_fields(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="vendor", password="secret123")
    store = Store.objects.create(
        owner=owner,
        name="Demo Store",
        slug="demo-store",
        description="",
        city="Москва",
        logo_url="",
        is_active=True,
        metadata={
            "tags": ["premium", "local"],
            "delivery_eta_minutes": 45,
            "delivery_price": 0,
            "currency": "RUB",
        },
    )
    product = Product.objects.create(
        store=store,
        title="Гранола",
        slug="granola",
        description="",
        price=Decimal("390.00"),
        currency="RUB",
        weight_grams=250,
        tags=["granola"],
        nutrition={"calories": 320, "protein_g": 22, "fat_g": 9, "carbs_g": 35},
        metadata={
            "subtitle": "22 г белка",
            "brand": "NutriCraft",
            "image_url": "https://example.com/granola.jpg",
            "discount_percent": 12,
            "price_original": 450,
            "badges": ["хит"],
            "rating": 4.5,
            "rating_count": 18,
        },
        is_published=True,
    )
    Inventory.objects.create(product=product, quantity=15, reserved=3, reorder_threshold=2)

    api_client.force_authenticate(user=owner)
    response = api_client.get(reverse("market:market-product-list"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    item = payload["results"][0]
    assert item["store_name"] == store.name
    assert item["subtitle"] == "22 г белка"
    assert item["inventory_available"] == 12
    assert item["available"] is True
    assert item["badges"] == ["хит"]
    assert float(item["price"]) == pytest.approx(390.0)
    assert float(item["price_original"]) == pytest.approx(450.0)
    assert float(item["discount_percent"]) == pytest.approx(12.0)
    assert float(item["rating"]) == pytest.approx(4.5)
    assert item["rating_count"] == 18


@pytest.mark.django_db
def test_store_viewset_flattens_metadata(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="vendor2", password="secret123")
    store = Store.objects.create(
        owner=owner,
        name="Healthy Foods",
        slug="healthy-foods",
        description="",
        city="Санкт-Петербург",
        metadata={
            "tags": ["organic"],
            "delivery_eta_minutes": 35,
            "delivery_price": 150,
            "currency": "RUB",
            "hero_image_url": "https://example.com/hero.jpg",
            "link_url": "https://example.com",
            "rating": 4.7,
            "rating_count": 54,
            "is_online": True,
        },
        is_active=True,
    )

    api_client.force_authenticate(user=owner)
    response = api_client.get(reverse("market:market-store-list"))
    assert response.status_code == 200
    data = response.json()["results"][0]
    assert data["tags"] == ["organic"]
    assert data["delivery_eta_minutes"] == 35
    assert float(data["delivery_price"]) == pytest.approx(150.0)
    assert data["hero_image_url"].startswith("https://example.com")
    assert data["is_online"] is True
    assert float(data["rating"]) == pytest.approx(4.7)
    assert data["rating_count"] == 54


@pytest.mark.django_db
def test_recipe_viewset_exposes_nutrition(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="chef", password="secret123")
    store = Store.objects.create(
        owner=owner,
        name="Kitchen Lab",
        slug="kitchen-lab",
        description="",
        city="Казань",
        metadata={},
        is_active=True,
    )
    recipe = Recipe.objects.create(
        store=store,
        author=owner,
        title="Боул",
        slug="bowl",
        summary="",
        cooking_time_minutes=10,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={
            "subtitle": "За 10 минут",
            "nutrition": {"calories": 420, "protein_g": 25, "fat_g": 12, "carbs_g": 48},
            "price": {"value": 250, "currency": "RUB"},
            "rating": 4.9,
            "rating_count": 8,
            "tags": ["breakfast"],
        },
    )

    api_client.force_authenticate(user=owner)
    response = api_client.get(reverse("market:market-recipe-list"))
    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["store_name"] == store.name
    assert item["subtitle"] == "За 10 минут"
    assert float(item["calories"]) == pytest.approx(420.0)
    assert float(item["protein_g"]) == pytest.approx(25.0)
    assert float(item["fat_g"]) == pytest.approx(12.0)
    assert float(item["carbs_g"]) == pytest.approx(48.0)
    assert float(item["price"]) == pytest.approx(250.0)
    assert item["currency"] == "RUB"
    assert float(item["rating"]) == pytest.approx(4.9)
    assert item["rating_count"] == 8
    assert item["tags"] == ["breakfast"]
