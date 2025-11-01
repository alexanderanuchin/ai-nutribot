import pytest

from django.urls import reverse
from rest_framework.test import APIClient

from apps.market.models import Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    """DRF API client that authenticates through JWT-compatible mechanisms."""

    return APIClient()


@pytest.mark.django_db
def test_search_endpoint_returns_results(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="demo", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Гранола & Ко",
        slug="granola-co",
        description="Лучшие завтраки",
        city="Москва",
        metadata={"tags": ["premium"], "hero_image_url": "https://placehold.co/1000x600"},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Гранола лесные ягоды",
        slug="granola-forest",
        description="Полезный завтрак",
        price="420.00",
        currency="RUB",
        weight_grams=250,
        tags=["granola", "organic"],
        nutrition={"calories": 320},
        metadata={"brand": "NutriCraft", "origin": "local", "discount_percent": 10},
        is_published=True,
    )
    Recipe.objects.create(
        store=store,
        title="Гранола боул",
        slug="granola-bowl",
        summary="Быстрый завтрак",
        cooking_time_minutes=5,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={"category": "breakfast", "tags": ["granola"]},
    )

    search_term = "Гранола"
    response = api_client.get(reverse("market:market-search"), {"q": search_term, "limit": 6})
    assert response.status_code == 200
    data = response.json()
    assert data["query"].casefold() == search_term.casefold()
    assert data["resource"] == "all"
    assert data["total"] >= 2, data
    assert any(result["resource"] == "products" for result in data["results"])
    assert any(result["resource"] == "recipes" for result in data["results"])
    assert "quick_filters" in data["suggestions"]
    assert data["suggestions"]["quick_filters"]


@pytest.mark.django_db
def test_search_honors_resource_filter(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="demo2", password="secret123")
    api_client.force_authenticate(user=user)

    store = Store.objects.create(
        owner=user,
        name="Express Store",
        slug="express",
        description="",
        city="Москва",
        metadata={"tags": ["express"], "hero_image_url": "https://placehold.co/640x360"},
        is_active=True,
    )
    Product.objects.create(
        store=store,
        title="Органическое молоко",
        slug="organic-milk",
        description="",
        price="220.00",
        currency="RUB",
        weight_grams=1000,
        tags=["organic"],
        nutrition={},
        metadata={"origin": "local"},
        is_published=True,
    )

    response = api_client.get(reverse("market:market-search"), {"resource": "products", "limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert all(result["resource"] == "products" for result in data["results"])


@pytest.mark.django_db
def test_search_respects_rating_protein_and_price_filters(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="qa", password="secret123")
    api_client.force_authenticate(user=user)

    premium_store = Store.objects.create(
        owner=user,
        name="Nutri Kitchen",
        slug="nutri-kitchen",
        description="",
        city="Москва",
        metadata={
            "tags": ["premium"],
            "hero_image_url": "https://placehold.co/800x400",
            "rating": 4.6,
            "rating_count": 42,
        },
        is_active=True,
    )
    budget_store = Store.objects.create(
        owner=user,
        name="Everyday Market",
        slug="everyday-market",
        description="",
        city="Москва",
        metadata={
            "tags": ["budget"],
            "hero_image_url": "https://placehold.co/640x360",
            "rating": 3.2,
            "rating_count": 11,
        },
        is_active=True,
    )

    product_top = Product.objects.create(
        store=premium_store,
        title="Протеиновый батончик",
        slug="protein-bar",
        description="",
        price="190.00",
        currency="RUB",
        weight_grams=60,
        tags=["snack"],
        nutrition={},
        metadata={"rating": 4.7, "rating_count": 18},
        is_published=True,
    )
    Product.objects.create(
        store=premium_store,
        title="Злаковый батончик",
        slug="grain-bar",
        description="",
        price="120.00",
        currency="RUB",
        weight_grams=60,
        tags=["snack"],
        nutrition={},
        metadata={"rating": 3.1, "rating_count": 4},
        is_published=True,
    )

    recipe_best = Recipe.objects.create(
        store=premium_store,
        title="Боул с киноа",
        slug="quinoa-bowl",
        summary="",
        cooking_time_minutes=20,
        servings=2,
        difficulty="medium",
        is_public=True,
        metadata={
            "rating": 4.8,
            "rating_count": 26,
            "nutrition": {"protein_g": 32, "calories": 520},
            "price": {"value": 280, "currency": "RUB"},
        },
    )
    Recipe.objects.create(
        store=premium_store,
        title="Смузи",
        slug="smoothie",
        summary="",
        cooking_time_minutes=5,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={
            "rating": 3.4,
            "rating_count": 7,
            "nutrition": {"protein_g": 6, "calories": 210},
            "price": {"value": 360, "currency": "RUB"},
        },
    )

    response = api_client.get(
        reverse("market:market-search"),
        {
            "resource": "recipes",
            "limit": 5,
            "min_rating": 4,
            "min_protein": 20,
            "max_price": 300,
        },
    )
    assert response.status_code == 200
    recipes_payload = response.json()
    assert recipes_payload["total"] >= 1
    assert all(result["resource"] == "recipes" for result in recipes_payload["results"])
    assert {item["id"] for item in recipes_payload["results"]} == {recipe_best.id}

    response = api_client.get(
        reverse("market:market-search"),
        {"resource": "products", "limit": 5, "min_rating": 4},
    )
    assert response.status_code == 200
    products_payload = response.json()
    assert {item["id"] for item in products_payload["results"]} == {product_top.id}

    response = api_client.get(
        reverse("market:market-search"),
        {"resource": "stores", "limit": 5, "min_rating": 4},
    )
    assert response.status_code == 200
    stores_payload = response.json()
    assert {item["id"] for item in stores_payload["results"]} == {premium_store.id}
