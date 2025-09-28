from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model

from apps.catalog.models import MenuItem, Nutrients, Restaurant
from apps.nutrition.models import MenuPlan
from apps.nutrition.services.menu_plan_service import MenuPlanService
from apps.users.models import Profile

User = get_user_model()


@pytest.fixture()
def auth_client(db):
    user = User.objects.create_user(username="tester", password="pass1234")
    profile = user.profile
    profile.city = "Moscow"
    profile.height_cm = 178
    profile.weight_kg = Decimal("80.0")
    profile.activity_level = Profile.Activity.MODERATE
    profile.goal = Profile.Goal.MAINTAIN
    profile.daily_budget = Decimal("950.00")
    profile.save()

    restaurant = Restaurant.objects.create(name="Cafe", city="Moscow")
    for idx in range(4):
        nutrient = Nutrients.objects.create(
            calories=400 + idx * 40,
            protein=32,
            fat=12,
            carbs=45,
        )
        MenuItem.objects.create(
            source="restaurant",
            source_id=restaurant.id,
            title=f"Dish {idx}",
            price=450 + idx * 15,
            is_available=True,
            nutrients=nutrient,
            tags=["popular"],
        )

    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client, user


@pytest.mark.django_db
def test_generate_and_save_sync(auth_client):
    client, user = auth_client
    response = client.post(
        "/api/nutrition/generate_and_save/",
        {"period_days": 7},
        format="json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert "plan_id" in payload
    assert payload["status"] == "generated"
    plan = MenuPlan.objects.get(id=payload["plan_id"])
    assert plan.user == user
    assert payload["summary"]["period_days"] == 7


@pytest.mark.django_db
def test_generate_and_save_async(auth_client, monkeypatch):
    client, user = auth_client
    applied = {}

    class DummyResult:
        def __init__(self):
            self.state = "UNKNOWN"

    def fake_async_result(job_id):
        applied["job_id"] = job_id
        return DummyResult()

    def fake_apply_async(*, kwargs, task_id):
        applied["kwargs"] = kwargs
        applied["task_id"] = task_id

    monkeypatch.setattr("apps.nutrition.api.nutrition.AsyncResult", fake_async_result)
    monkeypatch.setattr(
        "apps.nutrition.api.nutrition.generate_menu_task.apply_async",
        fake_apply_async,
    )

    response = client.post(
        "/api/nutrition/generate_and_save/",
        {"period_days": 14, "overrides": {"meal_times": ["breakfast", "lunch", "dinner"]}},
        format="json",
    )
    assert response.status_code == 202
    payload = response.json()
    assert "job_id" in payload
    assert applied["task_id"].startswith(f"user:{user.id}:")
    assert applied["kwargs"]["user_id"] == user.id
    assert applied["kwargs"]["params"]["period_days"] == 14


@pytest.mark.django_db
def test_job_status_endpoint(auth_client, monkeypatch):
    client, user = auth_client

    class SuccessResult:
        state = "SUCCESS"
        result = {"plan_id": 1, "summary": {"period_days": 7}}

    monkeypatch.setattr("apps.nutrition.api.nutrition.AsyncResult", lambda job_id: SuccessResult())

    job_id = f"user:{user.id}:generate:7:abc"
    response = client.get(f"/api/nutrition/jobs/{job_id}/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["plan_id"] == 1
    assert payload["summary"]["period_days"] == 7


@pytest.mark.django_db
def test_latest_and_history_endpoints(auth_client):
    client, user = auth_client
    service = MenuPlanService()
    plan, summary = service.generate_and_save(user=user, params={"period_days": 7})

    latest_response = client.get("/api/nutrition/plans/latest/")
    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["plan_id"] == plan.id
    assert latest_payload["summary"]["period_days"] == 7

    history_response = client.get("/api/nutrition/plans/history/?limit=5")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["plan_id"] == plan.id


@pytest.mark.django_db
def test_accept_and_reject_endpoints(auth_client):
    client, user = auth_client
    service = MenuPlanService()
    plan, _ = service.generate_and_save(user=user, params={"period_days": 7})

    accept_response = client.post(f"/api/nutrition/plans/{plan.id}/accept/")
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    reject_response = client.post(f"/api/nutrition/plans/{plan.id}/reject/")
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"


@pytest.mark.django_db
def test_generate_failure_returns_server_error(auth_client):
    client, user = auth_client
    response = client.post(
        "/api/nutrition/generate_and_save/",
        {"period_days": 7, "overrides": {"city": "Nonexistent"}},
        format="json",
    )
    assert response.status_code == 500
    assert "detail" in response.json()