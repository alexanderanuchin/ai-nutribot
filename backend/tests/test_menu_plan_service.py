import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.catalog.models import MenuItem, Nutrients, Restaurant
from apps.nutrition.models import MenuPlan, MenuPlanSnapshot
from apps.nutrition.services.menu_plan_service import (
    MenuPlanEngineError,
    MenuPlanService,
)
from apps.users.models import Profile

User = get_user_model()


@pytest.fixture
def user_with_profile(db):
    user = User.objects.create_user(username="test", password="pass")
    profile = user.profile
    profile.sex = Profile.Sex.MALE
    profile.height_cm = 180
    profile.weight_kg = Decimal("82.0")
    profile.activity_level = Profile.Activity.MODERATE
    profile.goal = Profile.Goal.MAINTAIN
    profile.daily_budget = Decimal("900.00")
    profile.allergies = []
    profile.save()
    return user


@pytest.fixture
def menu_items(db):
    restaurant = Restaurant.objects.create(name="Test", city="Moscow")
    nutrients = [
        Nutrients.objects.create(calories=420 + idx * 50, protein=30, fat=15, carbs=40)
        for idx in range(3)
    ]
    items = []
    for idx, nutrient in enumerate(nutrients, start=1):
        items.append(
            MenuItem.objects.create(
                source="restaurant",
                source_id=restaurant.id,
                title=f"Dish {idx}",
                price=450 + idx * 10,
                is_available=True,
                nutrients=nutrient,
                tags=["test"],
            )
        )
    return items


@pytest.fixture
def service():
    return MenuPlanService()


@pytest.mark.django_db
def test_generate_and_save_creates_plan(user_with_profile, menu_items, service):
    user = user_with_profile
    plan, summary = service.generate_and_save(user=user, params={"period_days": 7})

    assert isinstance(plan, MenuPlan)
    assert summary["period_days"] == 7
    assert plan.meals.count() == summary["meals_total"]
    snapshot = plan.snapshot
    assert snapshot.metadata["fallback_used"] is True
    assert snapshot.summary["estimated_cost_rub_per_day"].endswith(".00")


@pytest.mark.django_db
def test_generate_and_save_is_idempotent(user_with_profile, menu_items, service):
    user = user_with_profile
    first_plan, _ = service.generate_and_save(user=user, params={"period_days": 7})
    second_plan, _ = service.generate_and_save(user=user, params={"period_days": 7})
    assert first_plan.id == second_plan.id
    assert MenuPlanSnapshot.objects.count() == 1


@pytest.mark.django_db
def test_generate_and_save_engine_failure(user_with_profile, menu_items, service):
    user = user_with_profile
    params = {"period_days": 7, "overrides": {"city": "Nowhere"}}
    with pytest.raises(MenuPlanEngineError):
        service.generate_and_save(user=user, params=params)


@pytest.mark.django_db
def test_accept_and_reject_update_status(user_with_profile, menu_items, service):
    user = user_with_profile
    plan, _ = service.generate_and_save(user=user, params={"period_days": 7})
    service.accept_plan(user=user, plan_id=plan.id)
    plan.refresh_from_db()
    assert plan.status == MenuPlan.Status.ACCEPTED
    service.reject_plan(user=user, plan_id=plan.id)
    plan.refresh_from_db()
    assert plan.status == MenuPlan.Status.REJECTED