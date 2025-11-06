import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.models import MealPlan, MealPlanItem, Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _create_store(user, name: str = "Wellness Kitchen") -> Store:
    return Store.objects.create(
        owner=user,
        name=name,
        slug=name.lower().replace(" ", "-"),
        city="Москва",
        description="",
        metadata={},
        is_active=True,
    )


def _create_recipe(store: Store, title: str = "Смузи энергия") -> Recipe:
    return Recipe.objects.create(
        store=store,
        title=title,
        slug=title.lower().replace(" ", "-"),
        summary="",
        cooking_time_minutes=10,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={
            "nutrition": {
                "calories": 320,
                "protein_g": 24,
                "fat_g": 8,
                "carbs_g": 30,
            },
            "price": {"value": 450, "currency": "RUB"},
            "hero_image_url": "https://img.example/smoothie.jpg",
            "preview_image_url": "https://img.example/smoothie-preview.jpg",
        },
    )


def _create_product(store: Store, title: str = "Батончик") -> Product:
    return Product.objects.create(
        store=store,
        title=title,
        slug=title.lower().replace(" ", "-"),
        description="",
        price="250.00",
        currency="RUB",
        weight_grams=60,
        nutrition={
            "calories": 210,
            "protein_g": 12,
            "fat_g": 9,
            "carbs_g": 19,
        },
        metadata={"image_url": "https://img.example/bar.jpg"},
        is_published=True,
    )


@pytest.mark.django_db
def test_meal_plan_creation_with_price(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="planner", password="secret123")
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("market:market-meal-plan-list"),
        {
            "title": "План недели",
            "description": "Фокус на баланс БЖУ",
            "start_date": timezone.now().date().isoformat(),
            "price_amount": "1290.00",
            "price_currency": "RUB",
            "metadata": {"targets": {"calories": 1800, "protein_g": 120, "fat_g": 50, "carbs_g": 200}},
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["price_amount"] == "1290.00"
    assert payload["price_currency"] == "RUB"
    assert payload["metadata"]["targets"]["calories"] == 1800
    plan = MealPlan.objects.get(pk=payload["id"])
    assert plan.price_amount == pytest.approx(1290)
    assert plan.metadata["targets"]["protein_g"] == 120


@pytest.mark.django_db
def test_meal_plan_nutrition_totals_and_daily_breakdown(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="nutrition", password="secret123")
    store = _create_store(owner)
    recipe = _create_recipe(store)
    plan = MealPlan.objects.create(
        user=owner,
        title="Сбалансированная неделя",
        start_date=timezone.now().date(),
        metadata={"targets": {"calories": 2000}},
    )
    MealPlanItem.objects.create(
        meal_plan=plan,
        recipe=recipe,
        servings="2.0",
        scheduled_for=plan.start_date,
        meal_type="breakfast",
    )

    api_client.force_authenticate(user=owner)
    response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    totals = data["nutrition_totals"]
    assert totals["calories"] == pytest.approx(640)
    assert totals["protein_g"] == pytest.approx(48)
    assert totals["fat_g"] == pytest.approx(16)
    assert totals["carbs_g"] == pytest.approx(60)
    assert len(data["daily_breakdown"]) == 1
    day_entry = data["daily_breakdown"][0]
    assert day_entry["date"] == plan.start_date.isoformat()
    assert not day_entry["is_unscheduled"]
    item = data["items"][0]
    assert item["total_nutrition"]["calories"] == pytest.approx(640)
    assert item["recipe_snapshot"]["calories"] == pytest.approx(320)
    assert item["recipe_snapshot"]["hero_image_url"].endswith("smoothie.jpg")


@pytest.mark.django_db
def test_published_plan_accessible_for_other_user(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="owner", password="secret123")
    viewer = django_user_model.objects.create_user(username="viewer", password="secret123")
    store = _create_store(owner)
    recipe = _create_recipe(store, title="Боул")
    plan = MealPlan.objects.create(
        user=owner,
        title="Публичный план",
        start_date=timezone.now().date(),
        is_published=True,
        published_at=timezone.now(),
    )
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0", meal_type="lunch")

    api_client.force_authenticate(user=viewer)
    response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["is_published"] is True
    assert payload["items"]


@pytest.mark.django_db
def test_private_plan_hidden_from_other_user(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="owner2", password="secret123")
    stranger = django_user_model.objects.create_user(username="stranger", password="secret123")
    store = _create_store(owner, name="Private Store")
    recipe = _create_recipe(store, title="Салат")
    plan = MealPlan.objects.create(
        user=owner,
        title="Приватный план",
        start_date=timezone.now().date(),
        is_published=False,
    )
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0", meal_type="dinner")

    api_client.force_authenticate(user=stranger)
    response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_public_scope_lists_published_plans(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="catalog", password="secret123")
    other = django_user_model.objects.create_user(username="other", password="secret123")
    store = _create_store(owner, name="City Kitchen")
    recipe = _create_recipe(store, title="Суп")

    MealPlan.objects.create(
        user=owner,
        title="Секретный",
        start_date=timezone.now().date(),
        is_published=False,
    )
    published_plan = MealPlan.objects.create(
        user=owner,
        title="Для всех",
        start_date=timezone.now().date(),
        is_published=True,
        published_at=timezone.now(),
        price_amount="990.00",
    )
    MealPlanItem.objects.create(meal_plan=published_plan, recipe=recipe, servings="1.0")

    response = api_client.get(
        reverse("market:market-meal-plan-list"),
        {"scope": "public"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Для всех"
    assert data["results"][0]["price_amount"] == "990.00"

    api_client.force_authenticate(user=other)
    owner_list = api_client.get(reverse("market:market-meal-plan-list"))
    assert owner_list.status_code == status.HTTP_200_OK
    assert owner_list.json()["count"] == 0


@pytest.mark.django_db
def test_plan_publish_toggle_controls_visibility(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="publisher", password="secret123")
    viewer = django_user_model.objects.create_user(username="observer", password="secret123")
    store = _create_store(owner, name="Toggle Store")
    recipe = _create_recipe(store, title="Тосты")
    plan = MealPlan.objects.create(
        user=owner,
        title="Переключаемый",
        start_date=timezone.now().date(),
        is_published=False,
    )
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0")

    api_client.force_authenticate(user=owner)
    publish_response = api_client.patch(
        reverse("market:market-meal-plan-detail", args=[plan.id]),
        {"is_published": True},
        format="json",
    )
    assert publish_response.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    assert plan.is_published is True
    assert plan.published_at is not None

    api_client.force_authenticate(user=viewer)
    visible = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert visible.status_code == status.HTTP_200_OK

    api_client.force_authenticate(user=owner)
    unpublish_response = api_client.patch(
        reverse("market:market-meal-plan-detail", args=[plan.id]),
        {"is_published": False},
        format="json",
    )
    assert unpublish_response.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    assert plan.is_published is False
    assert plan.published_at is not None

    api_client.force_authenticate(user=viewer)
    hidden = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert hidden.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_plan_product_items_count_in_totals(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="products", password="secret123")
    store = _create_store(owner, name="Nutrition Store")
    product = _create_product(store, title="Протеиновый батончик")
    plan = MealPlan.objects.create(
        user=owner,
        title="Продукты",
        start_date=timezone.now().date(),
        metadata={"targets": {"calories": 2000}},
    )
    MealPlanItem.objects.create(
        meal_plan=plan,
        product=product,
        servings="1.5",
        meal_type="snack",
    )

    api_client.force_authenticate(user=owner)
    response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    totals = data["nutrition_totals"]
    assert totals["calories"] == pytest.approx(315)
    assert totals["protein_g"] == pytest.approx(18)
    assert totals["fat_g"] == pytest.approx(13.5)
    assert totals["carbs_g"] == pytest.approx(28.5)
    item = data["items"][0]
    assert item["product_snapshot"]["title"] == "Протеиновый батончик"
    assert item["total_nutrition"]["calories"] == pytest.approx(315)
