from datetime import timedelta

import csv
import io
import json

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
            "goal": "weight_loss",
            "tags": ["Detox", "Fresh-start"],
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
    assert payload["goal"] == "weight_loss"
    assert payload["tags"] == ["detox", "fresh-start"]
    assert payload["metadata"]["targets"]["calories"] == 1800
    plan = MealPlan.objects.get(pk=payload["id"])
    assert plan.price_amount == pytest.approx(1290)
    assert plan.metadata["targets"]["protein_g"] == 120
    assert plan.goal == "weight_loss"
    assert plan.tags == ["detox", "fresh-start"]


@pytest.mark.django_db
def test_meal_plan_nutrition_totals_and_daily_breakdown(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="nutrition", password="secret123")
    store = _create_store(owner)
    recipe = _create_recipe(store)
    start = timezone.now().date()
    plan = MealPlan.objects.create(
        user=owner,
        title="Сбалансированная неделя",
        start_date=start,
        end_date=start,
        metadata={"targets": {"calories": 2000}},
        goal="balanced",
        tags=["wellness"],
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
    assert data["total_calories"] == 640
    assert data["calories_per_day"] == 640
    assert data["duration_days"] == 1
    assert data["goal"] == "balanced"
    assert data["tags"] == ["wellness"]
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

    api_client.force_authenticate(user=None)
    anonymous_response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert anonymous_response.status_code == status.HTTP_200_OK
    payload = anonymous_response.json()
    assert payload["is_published"] is True
    assert payload["items"]

    api_client.force_authenticate(user=viewer)
    response = api_client.get(reverse("market:market-meal-plan-detail", args=[plan.id]))
    assert response.status_code == status.HTTP_200_OK


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
def test_public_filters_by_goal_duration_and_calories(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="filters", password="secret123")
    store = _create_store(owner, name="Filter Kitchen")
    recipe = _create_recipe(store, title="Рис")
    start = timezone.now().date()

    match_plan = MealPlan.objects.create(
        user=owner,
        title="Детокс",
        start_date=start,
        end_date=start + timedelta(days=6),
        is_published=True,
        published_at=timezone.now(),
        goal="balanced",
        tags=["detox"],
    )
    MealPlanItem.objects.create(meal_plan=match_plan, recipe=recipe, servings="1.0")

    other_plan = MealPlan.objects.create(
        user=owner,
        title="Другая цель",
        start_date=start,
        end_date=start + timedelta(days=13),
        is_published=True,
        published_at=timezone.now(),
        goal="muscle_gain",
        tags=["mass"],
    )
    MealPlanItem.objects.create(meal_plan=other_plan, recipe=recipe, servings="3.0")

    response = api_client.get(
        reverse("market:market-meal-plan-list"),
        {
            "scope": "public",
            "goal": "balanced",
            "duration": "7",
            "calories_min": "300",
            "calories_max": "900",
            "tag": "detox",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == match_plan.id
    assert payload["results"][0]["goal"] == "balanced"
    assert payload["results"][0]["total_calories"] >= 300
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
    start = timezone.now().date()
    plan = MealPlan.objects.create(
        user=owner,
        title="Продукты",
        start_date=start,
        end_date=start + timedelta(days=6),
        metadata={"targets": {"calories": 2000}},
        goal="balanced",
        tags=["protein"],
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
    assert data["total_calories"] == 315
    assert data["calories_per_day"] == 45
    assert data["duration_days"] == 7
    item = data["items"][0]
    assert item["product_snapshot"]["title"] == "Протеиновый батончик"
    assert item["total_nutrition"]["calories"] == pytest.approx(315)


@pytest.mark.django_db
def test_meal_plan_export_variants(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="exporter", password="secret123")
    store = _create_store(owner, name="Clinic Kitchen")
    recipe = _create_recipe(store, title="Овсяная каша")
    today = timezone.now().date()
    review_date = today + timedelta(days=14)
    description = {
        "format": "ncp-adime-v1",
        "language": "ru",
        "sections": {
            "intervention_goal": "Стабилизировать гликемию через контроль углеводов",
            "rationale": "Диагноз: предиабет, избыток простых сахаров.",
            "dietary_principles": "DASH + низкий ГИ, дробное питание",
            "client_recommendations": "Добавьте овощи в каждый приём, шаги ≥ 8к",
            "monitoring_plan": "Еженедельный отчёт в приложении, контроль АД",
            "follow_up_requirements": [
                "Вес и талия",
                "3-дневный дневник питания",
                "Фото ужинов",
            ],
            "next_review_date": review_date.isoformat(),
            "communication_tone": "поддерживающий профессиональный",
        },
    }
    plan = MealPlan.objects.create(
        user=owner,
        title="План предиабет",
        start_date=today,
        end_date=today + timedelta(days=6),
        description=json.dumps(description, ensure_ascii=False),
        metadata={"targets": {"calories": 1900, "protein_g": 120, "fat_g": 65, "carbs_g": 220}},
        price_amount="1990.00",
    )
    MealPlanItem.objects.create(
        meal_plan=plan,
        recipe=recipe,
        servings="1.0",
        scheduled_for=today,
        meal_type="breakfast",
    )

    api_client.force_authenticate(user=owner)

    html_response = api_client.get(
        reverse("market:market-meal-plan-export", args=[plan.id]),
        {"type": "client"},
    )
    assert html_response.status_code == status.HTTP_200_OK
    assert html_response["Content-Type"].startswith("text/html")
    html = html_response.content.decode("utf-8")
    assert "Цель вмешательства" in html
    assert "Что прислать к следующей встрече" in html

    specialist_response = api_client.get(
        reverse("market:market-meal-plan-export", args=[plan.id]),
        {"type": "specialist"},
    )
    assert specialist_response.status_code == status.HTTP_200_OK
    payload = json.loads(specialist_response.content.decode("utf-8"))
    assert payload["plan"]["title"] == "План предиабет"
    assert payload["ncp"]["assessment"]["goal"].startswith("Стабилизировать")
    assert payload["ncp"]["monitoring_evaluation"]["follow_up_requirements"][0] == "Вес и талия"
    assert payload["ncp"]["monitoring_evaluation"]["next_review_date"] == review_date.isoformat()
    assert payload["items"][0]["reference"]["title"] == "Овсяная каша"

    csv_response = api_client.get(
        reverse("market:market-meal-plan-export", args=[plan.id]),
        {"type": "table"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    rows = list(csv.reader(io.StringIO(csv_response.content.decode("utf-8"))))
    meta_rows: dict[str, str] = {}
    data_start_index = 0
    for index, row in enumerate(rows):
        if not row:
            data_start_index = index + 1
            break
        key = row[0]
        meta_rows[key] = row[1] if len(row) > 1 else ""
    assert meta_rows["plan_id"] == str(plan.id)
    assert meta_rows["intervention_goal"].startswith("Стабилизировать")
    assert meta_rows["next_review_date"] == review_date.isoformat()
    assert meta_rows["communication_tone"] == "поддерживающий профессиональный"
    assert meta_rows["follow_up_requirements"].startswith("Вес и талия")

    data_rows = rows[data_start_index + 1 :]
    assert data_rows[-1][0] == today.isoformat()
    assert data_rows[-1][3] == "Овсяная каша"


@pytest.mark.django_db
def test_meal_plan_export_denied_for_other_user(api_client, django_user_model):
    owner = django_user_model.objects.create_user(username="export-owner", password="secret123")
    stranger = django_user_model.objects.create_user(username="export-stranger", password="secret123")
    store = _create_store(owner, name="Clinic Lab")
    recipe = _create_recipe(store, title="Смузи детокс")
    plan = MealPlan.objects.create(user=owner, title="Private export", start_date=timezone.now().date())
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0")

    api_client.force_authenticate(user=stranger)
    response = api_client.get(
        reverse("market:market-meal-plan-export", args=[plan.id]),
        {"type": "client"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
