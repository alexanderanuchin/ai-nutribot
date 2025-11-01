import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.models import Cart, CartItem, MealPlanItem, Product, Recipe, Store


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_cart_submission_creates_and_updates_item(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="buyer", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="Эко лавка",
        slug="eco",
        city="Москва",
        description="",
        metadata={"tags": ["eco"]},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Органический чай",
        slug="organic-tea",
        description="",
        price="450.00",
        currency="RUB",
        weight_grams=100,
        is_published=True,
    )
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("market:market-cart-submit"),
        {"product_id": product.id, "quantity": 2},
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    data = create_response.json()
    assert data["status"] == "created"
    assert data["item"]["quantity"] == 2
    assert data["cart"]["items_quantity"] == 2

    update_response = api_client.post(
        reverse("market:market-cart-submit"),
        {"product_id": product.id, "quantity": 5},
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    payload = update_response.json()
    assert payload["status"] == "updated"
    assert payload["item"]["quantity"] == 5
    assert payload["cart"]["items_quantity"] == 5
    cart_item = CartItem.objects.get(product=product)
    assert cart_item.quantity == 5


@pytest.mark.django_db
def test_cart_submission_removes_item_on_zero_quantity(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="buyer2", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="Лавка специй",
        slug="spice-shop",
        city="Санкт-Петербург",
        description="",
        metadata={},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Кардамон",
        slug="cardamom",
        description="",
        price="120.00",
        currency="RUB",
        weight_grams=30,
        is_published=True,
    )
    cart_item = CartItem.objects.create(
        cart=user.market_carts.create(store=store, status=Cart.Status.ACTIVE),
        product=product,
        quantity=3,
        price_snapshot="120.00",
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("market:market-cart-submit"),
        {"product_id": product.id, "quantity": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "removed"
    assert data["item"] is None
    assert CartItem.objects.filter(id=cart_item.id).count() == 0


@pytest.mark.django_db
def test_plan_submission_creates_and_updates_item(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="planner", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="Фермерское меню",
        slug="farm-menu",
        city="Казань",
        description="",
        metadata={"tags": ["farm"]},
        is_active=True,
    )
    recipe = Recipe.objects.create(
        store=store,
        title="Запечённые овощи",
        slug="baked-veggies",
        summary="",
        cooking_time_minutes=20,
        servings=2,
        difficulty="easy",
        is_public=True,
    )
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("market:market-plan-submit"),
        {"recipe_id": recipe.id, "servings": "2"},
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    payload = create_response.json()
    assert payload["status"] == "created"
    assert pytest.approx(payload["item"]["servings"], rel=1e-3) == 2

    update_response = api_client.post(
        reverse("market:market-plan-submit"),
        {"recipe_id": recipe.id, "servings": "3.5"},
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()
    assert data["status"] == "updated"
    assert pytest.approx(data["item"]["servings"], rel=1e-3) == 3.5
    plan_item = MealPlanItem.objects.get(recipe=recipe)
    assert pytest.approx(float(plan_item.servings), rel=1e-3) == 3.5


@pytest.mark.django_db
def test_plan_submission_removes_item(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="planner2", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="План питания",
        slug="plan-store",
        city="Новосибирск",
        description="",
        metadata={},
        is_active=True,
    )
    recipe = Recipe.objects.create(
        store=store,
        title="Овсянка",
        slug="oatmeal",
        summary="",
        cooking_time_minutes=5,
        servings=1,
        difficulty="easy",
        is_public=True,
    )
    plan_item = MealPlanItem.objects.create(
        meal_plan=user.meal_plans.create(title="Авто", start_date=timezone.now().date()),
        recipe=recipe,
        servings="1.00",
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("market:market-plan-submit"),
        {"recipe_id": recipe.id, "servings": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "removed"
    assert data["item"] is None
    assert MealPlanItem.objects.filter(id=plan_item.id).count() == 0


@pytest.mark.django_db
def test_cart_submission_validates_product(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="validator", password="secret123")
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("market:market-cart-submit"),
        {"product_id": 999, "quantity": 1},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "product_id" in response.json()
