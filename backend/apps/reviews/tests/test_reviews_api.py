from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.models import MealPlan, MealPlanItem, Product, Recipe, Store


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="customer", password="secret123")


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username="friend", password="secret123")


@pytest.fixture
def api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def store(user) -> Store:
    return Store.objects.create(
        owner=user,
        name="Wellness Kitchen",
        slug="wellness-kitchen",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )


@pytest.fixture
def recipe(store) -> Recipe:
    return Recipe.objects.create(
        store=store,
        title="Смузи энергия",
        slug="smuzi-energiya",
        summary="",
        cooking_time_minutes=15,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={"price": {"value": 490, "currency": "RUB"}},
    )


@pytest.fixture
def product(store) -> Product:
    return Product.objects.create(
        store=store,
        title="Батончик",
        slug="batonchik",
        description="",
        price="250.00",
        currency="RUB",
        weight_grams=60,
        metadata={},
        is_published=True,
    )


@pytest.fixture
def meal_plan(user) -> MealPlan:
    plan = MealPlan.objects.create(
        user=user,
        title="План недели",
        start_date=timezone.now().date(),
        metadata={"purchased_user_ids": []},
    )
    return plan


@pytest.mark.django_db
def test_recipe_review_requires_interaction(api_client: APIClient, recipe: Recipe, user) -> None:
    url = reverse("reviews:review-list")
    response = api_client.post(
        url,
        {"target_type": "recipe", "target_id": recipe.id, "rating": 5, "text": "Отличный вкус"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    plan = MealPlan.objects.create(user=user, title="Испытание", start_date=timezone.now().date(), metadata={})
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0")

    response = api_client.post(
        url,
        {"target_type": "recipe", "target_id": recipe.id, "rating": 4, "text": "Повторю"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    recipe.refresh_from_db()
    assert recipe.metadata.get("rating") == 4
    assert recipe.metadata.get("rating_count") == 1


@pytest.mark.django_db
def test_product_reviews_update_average(api_client: APIClient, product: Product, user, other_user) -> None:
    plan = MealPlan.objects.create(
        user=user,
        title="Личный план",
        start_date=timezone.now().date(),
        metadata={},
    )
    MealPlanItem.objects.create(meal_plan=plan, product=product, servings="1.0")

    url = reverse("reviews:review-list")
    payload = {"target_type": "product", "target_id": product.id, "rating": 5, "text": "Вкусно"}
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    # second user also interacted via plan
    customer_plan = MealPlan.objects.create(
        user=other_user,
        title="План гостя",
        start_date=timezone.now().date(),
        metadata={},
    )
    MealPlanItem.objects.create(meal_plan=customer_plan, product=product, servings="2.0")
    client2 = APIClient()
    client2.force_authenticate(user=other_user)
    response = client2.post(url, {**payload, "rating": 3}, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    product.refresh_from_db()
    assert product.metadata.get("rating_count") == 2
    assert product.metadata.get("rating") == pytest.approx(4.0)


@pytest.mark.django_db
def test_duplicate_reviews_rejected(api_client: APIClient, recipe: Recipe, user) -> None:
    plan = MealPlan.objects.create(user=user, title="Чек", start_date=timezone.now().date(), metadata={})
    MealPlanItem.objects.create(meal_plan=plan, recipe=recipe, servings="1.0")
    url = reverse("reviews:review-list")
    payload = {"target_type": "recipe", "target_id": recipe.id, "rating": 5}
    first = api_client.post(url, payload, format="json")
    assert first.status_code == status.HTTP_201_CREATED
    second = api_client.post(url, payload, format="json")
    assert second.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_listing_recalculates_rating(api_client: APIClient, meal_plan: MealPlan, user, other_user) -> None:
    # simulate plan purchase by storing user id in metadata
    meal_plan.metadata = {"purchased_user_ids": [other_user.id]}
    meal_plan.save(update_fields=["metadata"])

    client2 = APIClient()
    client2.force_authenticate(user=other_user)
    url = reverse("reviews:review-list")
    payload = {"target_type": "plan", "target_id": meal_plan.id, "rating": 5, "text": "Работает"}
    response = client2.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    meal_plan.metadata["rating"] = 1
    meal_plan.save(update_fields=["metadata"])

    response = api_client.get(url, {"target_type": "plan", "target_id": meal_plan.id})
    assert response.status_code == status.HTTP_200_OK
    meal_plan.refresh_from_db()
    assert meal_plan.metadata.get("rating") == 5
    assert meal_plan.metadata.get("rating_count") == 1
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
