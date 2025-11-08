from __future__ import annotations

from decimal import Decimal
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.models import MealPlan, MealPlanItem, MealPlanAccess, Recipe, RecipeAccess, Store
from apps.orders.models import WalletTransaction
from apps.orders.services.wallet import wallet_topup


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _create_store(user) -> Store:
    return Store.objects.create(
        owner=user,
        name="Wellness Lab",
        slug=f"wellness-{user.id}",
        description="",
        city="Москва",
        metadata={},
        is_active=True,
    )


def _create_premium_recipe(store: Store, *, title: str = "Премиум смузи") -> Recipe:
    return Recipe.objects.create(
        store=store,
        author=store.owner,
        title=title,
        slug=f"{title.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        summary="Энергетический коктейль",
        cooking_time_minutes=10,
        servings=1,
        difficulty="easy",
        is_public=True,
        metadata={
            "is_premium": True,
            "price": {"value": 150, "currency": "STARS"},
            "nutrition": {
                "calories": 320,
                "protein_g": 24,
                "fat_g": 8,
                "carbs_g": 30,
            },
        },
    )


def _create_premium_plan(owner, recipe: Recipe) -> MealPlan:
    plan = MealPlan.objects.create(
        user=owner,
        title="Фокус на форму",
        description="7-дневный рацион",
        start_date=timezone.now().date(),
        price_amount="199",
        price_currency="STARS",
        is_published=True,
    )
    MealPlanItem.objects.create(
        meal_plan=plan,
        recipe=recipe,
        servings="1.0",
        meal_type="breakfast",
    )
    return plan


@pytest.mark.django_db
def test_recipe_purchase_with_sufficient_balance(api_client: APIClient, django_user_model):
    owner = django_user_model.objects.create_user(username="chef", password="secret123")
    store = _create_store(owner)
    recipe = _create_premium_recipe(store)

    buyer = django_user_model.objects.create_user(username="buyer", password="secret123")
    profile = buyer.profile

    wallet_topup(
        profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("300"),
        description="Тестовое пополнение",
    )

    api_client.force_authenticate(user=buyer)
    detail_url = reverse("market:market-recipe-detail", kwargs={"pk": recipe.id})
    purchase_url = reverse("market:market-recipe-purchase", kwargs={"pk": recipe.id})

    assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN

    response = api_client.post(purchase_url, {}, format="json", **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex})
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["price_stars"] == "150"
    assert payload["wallet_transaction_id"]

    access = RecipeAccess.objects.get(profile=profile, recipe=recipe)
    assert access.wallet_transaction is not None
    profile.refresh_from_db()
    assert profile.telegram_stars_balance == 150

    detail = api_client.get(detail_url)
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["has_access"] is True


@pytest.mark.django_db
def test_recipe_purchase_insufficient_balance(api_client: APIClient, django_user_model):
    owner = django_user_model.objects.create_user(username="chef2", password="secret123")
    store = _create_store(owner)
    recipe = _create_premium_recipe(store, title="Премиальный завтрак")

    buyer = django_user_model.objects.create_user(username="nobalance", password="secret123")
    api_client.force_authenticate(user=buyer)

    purchase_url = reverse("market:market-recipe-purchase", kwargs={"pk": recipe.id})
    response = api_client.post(purchase_url, {}, format="json", **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]
    assert RecipeAccess.objects.filter(profile=buyer.profile, recipe=recipe).count() == 0


@pytest.mark.django_db
def test_meal_plan_purchase_flow(api_client: APIClient, django_user_model):
    owner = django_user_model.objects.create_user(username="planner", password="secret123")
    store = _create_store(owner)
    recipe = _create_premium_recipe(store, title="Премиум боул")
    plan = _create_premium_plan(owner, recipe)

    buyer = django_user_model.objects.create_user(username="planbuyer", password="secret123")
    profile = buyer.profile

    api_client.force_authenticate(user=buyer)
    plan_detail = reverse("market:market-meal-plan-detail", kwargs={"pk": plan.id})
    purchase_url = reverse("market:market-meal-plan-purchase", kwargs={"pk": plan.id})

    assert api_client.get(plan_detail).status_code == status.HTTP_403_FORBIDDEN

    wallet_topup(
        profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("500"),
        description="Тестовое пополнение",
    )

    response = api_client.post(purchase_url, {}, format="json", **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex})
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["price_stars"] == "199"
    assert payload["wallet_transaction_id"]

    plan.refresh_from_db()
    assert profile.user_id in plan.metadata.get("purchased_user_ids", [])
    assert MealPlanAccess.objects.filter(profile=profile, meal_plan=plan).exists()

    detail = api_client.get(plan_detail)
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["has_access"] is True


@pytest.mark.django_db
def test_meal_plan_purchase_insufficient_balance(api_client: APIClient, django_user_model):
    owner = django_user_model.objects.create_user(username="planner2", password="secret123")
    store = _create_store(owner)
    recipe = _create_premium_recipe(store, title="Премиальный салат")
    plan = _create_premium_plan(owner, recipe)

    buyer = django_user_model.objects.create_user(username="plan-no-balance", password="secret123")
    api_client.force_authenticate(user=buyer)

    purchase_url = reverse("market:market-meal-plan-purchase", kwargs={"pk": plan.id})
    response = api_client.post(purchase_url, {}, format="json", **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert MealPlanAccess.objects.filter(profile=buyer.profile, meal_plan=plan).count() == 0


@pytest.mark.django_db
def test_purchase_after_manual_stars_topup(api_client: APIClient, django_user_model):
    owner = django_user_model.objects.create_user(username="chef3", password="secret123")
    store = _create_store(owner)
    recipe = _create_premium_recipe(store, title="Премиум латте")
    plan = _create_premium_plan(owner, recipe)

    buyer = django_user_model.objects.create_user(username="telegram-topup", password="secret123")
    profile = buyer.profile

    api_client.force_authenticate(user=buyer)
    purchase_url = reverse("market:market-meal-plan-purchase", kwargs={"pk": plan.id})

    # emulate telegram invoice top-up by crediting Stars into the wallet
    wallet_topup(
        profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("250"),
        description="Пополнение через Telegram",
    )

    response = api_client.post(purchase_url, {}, format="json", **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex})
    assert response.status_code == status.HTTP_201_CREATED
    assert MealPlanAccess.objects.filter(profile=profile, meal_plan=plan).exists()
