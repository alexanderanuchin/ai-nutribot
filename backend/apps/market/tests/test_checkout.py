from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.models import Cart, CartItem, Inventory, Product, Store
from apps.orders.models import Order
from apps.orders.services.wallet import wallet_topup


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_checkout_creates_pending_order(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="buyer", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="Зелёная лавка",
        slug="green-shop",
        city="Москва",
        description="",
        metadata={},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Органический чай",
        slug="organic-tea",
        description="",
        price=Decimal("450.00"),
        currency="RUB",
        weight_grams=100,
        is_published=True,
    )
    Inventory.objects.create(product=product, quantity=25, reserved=0)
    cart = Cart.objects.create(user=user, store=store, status=Cart.Status.ACTIVE, currency="RUB")
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2,
        price_snapshot=product.price,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("market:market-cart-checkout", args=[cart.id]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["paid"] is False
    order_data = payload["order"]
    assert order_data["status"] == Order.Status.PENDING_PAYMENT
    assert order_data["currency"] == "rub"
    assert Decimal(str(order_data["amount"])) == Decimal("900.00")

    order = Order.objects.get(pk=order_data["id"])
    assert order.kind == Order.Kind.DIGITAL_PRODUCT
    assert order.total_price == Decimal("900.00")
    assert order.metadata["cart_id"] == cart.id
    assert order.metadata["items"][0]["product_id"] == product.id

    cart.refresh_from_db()
    assert cart.status == Cart.Status.CHECKED_OUT
    assert cart.metadata["order_id"] == order.id


@pytest.mark.django_db
def test_checkout_with_wallet_payment_reduces_inventory(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="buyer_wallet", password="secret123")
    profile = user.profile
    store = Store.objects.create(
        owner=user,
        name="Фитнес маркет",
        slug="fitness-shop",
        city="Санкт-Петербург",
        description="",
        metadata={},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Протеиновый батончик",
        slug="protein-bar",
        description="",
        price=Decimal("50.00"),
        currency="RUB",
        weight_grams=60,
        is_published=True,
    )
    inventory = Inventory.objects.create(product=product, quantity=30, reserved=0)
    cart = Cart.objects.create(user=user, store=store, status=Cart.Status.ACTIVE)
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=3,
        price_snapshot=Decimal("50.00"),
    )

    wallet_topup(profile, currency="STARS", amount=300, description="test topup")

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("market:market-cart-checkout", args=[cart.id]),
        {"pay_with_wallet": True, "wallet_currency": "stars"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["paid"] is True
    order_payload = payload["order"]
    assert order_payload["status"] == Order.Status.PAID
    assert order_payload["currency"] == "stars"
    assert order_payload["amount"] == 150

    order = Order.objects.get(pk=order_payload["id"])
    assert order.wallet_currency == Order.Currency.TELEGRAM_STARS

    inventory.refresh_from_db()
    assert inventory.quantity == 27


@pytest.mark.django_db
def test_checkout_wallet_insufficient_funds_returns_error(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="buyer_fail", password="secret123")
    store = Store.objects.create(
        owner=user,
        name="Эко ферма",
        slug="eco-farm",
        city="Новосибирск",
        description="",
        metadata={},
        is_active=True,
    )
    product = Product.objects.create(
        store=store,
        title="Орехи",
        slug="nuts",
        description="",
        price=Decimal("120.00"),
        currency="RUB",
        weight_grams=250,
        is_published=True,
    )
    Inventory.objects.create(product=product, quantity=10, reserved=0)
    cart = Cart.objects.create(user=user, store=store, status=Cart.Status.ACTIVE)
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=1,
        price_snapshot=product.price,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("market:market-cart-checkout", args=[cart.id]),
        {"pay_with_wallet": True, "wallet_currency": "CALO"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "pay_with_wallet" in body

    cart.refresh_from_db()
    assert cart.status == Cart.Status.ACTIVE
    assert "order_id" not in cart.metadata
    assert Order.objects.count() == 0
