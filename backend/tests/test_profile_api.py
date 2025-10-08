import pytest
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.orders.models import WalletTransaction
from apps.users.models import Profile
from apps.users.services import sync_stars_ledger_for_transaction


@pytest.fixture()
def auth_client(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="+79991234567",
        password="StrongPass!1",
        email="user@example.com",
        first_name="Ivan",
        last_name="Petrov",
    )
    profile = user.profile
    profile.city = "Москва"
    profile.daily_budget = Decimal("1234.56")
    profile.allergies = ["nuts"]
    profile.goal = Profile.Goal.LOSE
    profile.save()

    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, user


@pytest.fixture()
def staff_client(db, settings):
    user_model = get_user_model()
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    user = user_model.objects.create_user(
        username="+79990009988",
        password="StrongPass!1",
        email="staff@example.com",
        is_staff=True,
    )
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, user


@pytest.mark.django_db
def test_get_profile_summary_returns_wallet_stub(auth_client):
    client, user = auth_client

    response = client.get("/api/users/me/profile/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["phone"] == user.username
    assert payload["profile"]["city"] == "Москва"
    assert payload["profile"]["budget"] == "1234.56"
    assert payload["profile"]["goals"] == "lose_weight"
    assert payload["wallet"] == {"stars": "0", "calo": "0.00"}


@pytest.mark.django_db
def test_patch_profile_updates_budget_and_goal(auth_client):
    client, user = auth_client

    response = client.patch(
        "/api/users/me/profile/update/",
        {
            "city": "Казань",
            "budget": "990.50",
            "allergies": ["gluten", "soy"],
            "goals": "gain_muscle",
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["city"] == "Казань"
    assert payload["profile"]["budget"] == "990.50"
    assert payload["profile"]["goals"] == "gain_muscle"
    assert set(payload["profile"]["allergies"]) == {"gluten", "soy"}

    user.refresh_from_db()
    profile = user.profile
    assert profile.city == "Казань"
    assert profile.daily_budget == Decimal("990.50")
    assert profile.goal == Profile.Goal.GAIN
    assert profile.allergies == ["gluten", "soy"]


@pytest.mark.django_db
def test_patch_profile_rejects_invalid_input(auth_client):
    client, user = auth_client
    other = get_user_model().objects.create_user(
        username="+79990001122",
        password="StrongPass!2",
        email="other@example.com",
    )

    response = client.patch(
        "/api/users/me/profile/update/",
        {"budget": -10, "phone": other.username},
        format="json",
    )

    assert response.status_code == 400
    errors = response.json()
    assert "budget" in errors
    assert "phone" in errors


@pytest.mark.django_db
def test_me_stars_endpoint_returns_ledger_balance(auth_client):
    client, user = auth_client
    profile = user.profile
    tx = WalletTransaction.objects.create(
        profile=profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        direction=WalletTransaction.Direction.CREDIT,
        status=WalletTransaction.Status.CONFIRMED,
        amount=Decimal("50"),
        balance_before=Decimal("0"),
        balance_after=Decimal("50"),
        description="Test topup",
        metadata={},
    )
    sync_stars_ledger_for_transaction(tx)

    response = client.get("/api/me/stars/")
    assert response.status_code == 200
    data = response.json()
    assert data["balance"]["amount"] == 50
    assert data["balance"]["currency"] == "XTR"
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["amount"] == 50
    assert data["transactions"][0]["direction"] == "in"


@pytest.mark.django_db
def test_bot_stars_balance_endpoint(staff_client):
    client, user = staff_client
    with mock.patch("apps.users.services.stars.httpx.Client") as mocked_client:
        instance = mocked_client.return_value.__enter__.return_value
        response_mock = instance.get.return_value
        response_mock.raise_for_status.return_value = None
        response_mock.json.return_value = {"ok": True, "result": {"star_count": 4321}}

        response = client.get("/api/admin/stars/bot-balance/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["balance"]["amount"] == 4321
    assert payload["balance"]["currency"] == "XTR"