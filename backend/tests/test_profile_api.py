import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Profile


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