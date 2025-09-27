from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.orders.models import Order, WalletPerk, WalletTarget, WalletTransaction

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user() -> User:
    return User.objects.create_user(
        username="+79990001122",
        email="wallet@example.com",
        password="StrongPass!1",
    )


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_wallet_topup_and_withdraw(auth_client: APIClient, user: User):
    resp = auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "stars", "amount": "300", "description": "Пополнение тест"},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["direction"] == WalletTransaction.Direction.CREDIT
    user.profile.refresh_from_db()
    assert user.profile.telegram_stars_balance == 300

    resp = auth_client.post(
        "/api/orders/wallet/transactions/withdraw/",
        {"currency": "stars", "amount": "120"},
        format="json",
    )
    assert resp.status_code == 201
    user.profile.refresh_from_db()
    assert user.profile.telegram_stars_balance == 180

    resp = auth_client.post(
        "/api/orders/wallet/transactions/withdraw/",
        {"currency": "stars", "amount": "1000"},
        format="json",
    )
    assert resp.status_code == 400
    assert "amount" in resp.json()


@pytest.mark.django_db
def test_wallet_summary_contains_targets_and_transactions(auth_client: APIClient, user: User):
    WalletPerk.objects.create(
        profile=user.profile,
        title="Бесплатная доставка",
        description="для заказов от 2000₽",
        priority=1,
    )
    WalletTarget.objects.create(
        profile=user.profile,
        currency=WalletTransaction.Currency.CALOCOIN,
        target_amount=Decimal("900.00"),
        label="До расширенного PRO",
        progress_template="Осталось {left} CaloCoin до полного доступа.",
        completed_template="CaloCoin достаточно — обновите PRO прямо сейчас.",
        priority=1,
    )

    auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "450.50", "description": "Первый платёж"},
        format="json",
    )
    resp = auth_client.get("/api/orders/wallet/summary/")
    assert resp.status_code == 200
    data = resp.json()
    assert "targets" in data
    calo_target = data["targets"]["calo"]
    assert calo_target["balance"] >= 450
    assert calo_target["target"] == pytest.approx(900.0)
    assert calo_target.get("label") == "До расширенного PRO"
    assert calo_target.get("progress_message").startswith("Осталось")
    assert calo_target.get("completed_message").startswith("CaloCoin достаточно")
    assert any(tx["description"] == "Первый платёж" for tx in data["recent_transactions"])
    assert "Бесплатная доставка — для заказов от 2000₽" in data["perks"]


@pytest.mark.django_db
def test_create_and_pay_order_via_wallet(auth_client: APIClient, user: User):
    auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "800"},
        format="json",
    )
    resp = auth_client.post(
        "/api/orders/wallet/orders/",
        {
            "title": "PRO подписка",
            "kind": "pro_subscription",
            "currency": "calo",
            "amount": "500",
            "pay_with_wallet": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["status"] == Order.Status.PAID
    user.profile.refresh_from_db()
    assert float(user.profile.calocoin_balance) == pytest.approx(300.0)

    order_id = payload["id"]
    order = Order.objects.get(pk=order_id)
    assert order.payment_transaction is not None
    assert order.payment_transaction.direction == WalletTransaction.Direction.DEBIT


@pytest.mark.django_db
def test_order_pay_endpoint(auth_client: APIClient, user: User):
    auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "stars", "amount": "500"},
        format="json",
    )
    create_resp = auth_client.post(
        "/api/orders/wallet/orders/",
        {
            "title": "Консультация",
            "kind": "consultation",
            "currency": "stars",
            "amount": "300",
            "pay_with_wallet": False,
        },
        format="json",
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    pay_resp = auth_client.post(
        f"/api/orders/wallet/orders/{order_id}/pay/",
        {"description": "Оплата консультации"},
        format="json",
    )
    assert pay_resp.status_code == 200
    data = pay_resp.json()
    assert data["status"] == Order.Status.PAID
    user.profile.refresh_from_db()
    assert user.profile.telegram_stars_balance == 200

    list_resp = auth_client.get("/api/orders/wallet/orders/")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == order_id for item in items)


@pytest.mark.django_db
def test_wallet_summary_creates_profile_if_missing(api_client: APIClient):
    user = User.objects.create_user(
        username="no-profile",
        email="orphan@example.com",
        password="StrongPass!1",
    )
    # Simulate legacy accounts created before automatic profile creation
    user.profile.delete()

    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/orders/wallet/summary/")

    assert resp.status_code == 200
    # A new profile should be created transparently
    user = User.objects.get(pk=user.pk)
    assert hasattr(user, "profile")
    assert user.profile is not None

    payload = resp.json()
    assert "targets" in payload
    assert payload["targets"]["stars"]["balance"] == 0