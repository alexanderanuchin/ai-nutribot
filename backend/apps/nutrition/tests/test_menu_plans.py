import copy
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalog.models import MenuItem, Nutrients, Restaurant
from apps.nutrition.models import MenuPlan

User = get_user_model()


def _make_payload(item: MenuItem, *, qty: float = 1.0, time_hint: str = "any", title: str | None = None):
    base = {
        "targets": {
            "calories": 2100,
            "protein_g": 130,
            "fat_g": 70,
            "carbs_g": 220,
        },
        "plan": [
            {
                "item_id": item.id,
                "qty": qty,
                "time_hint": time_hint,
                "title": title or item.title,
            }
        ],
    }
    return copy.deepcopy(base)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="user@example.com", password="StrongPass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other@example.com", password="StrongPass123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def menu_item(db):
    restaurant = Restaurant.objects.create(name="Test Cafe", city="City")
    nutrients = Nutrients.objects.create(calories=520, protein=32, fat=18, carbs=55)
    return MenuItem.objects.create(
        source="restaurant",
        source_id=restaurant.id,
        title="Салат с киноа",
        price=350,
        nutrients=nutrients,
    )


@pytest.mark.django_db
def test_generate_menu_creates_plan_and_returns_identifier(api_client, user, menu_item, monkeypatch):
    payload = _make_payload(menu_item, qty=1.5, time_hint="breakfast")

    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: payload)

    response = api_client.post("/api/nutrition/generate/", format="json")
    assert response.status_code == 200
    data = response.json()

    assert data["plan_id"] > 0
    assert data["status"] == MenuPlan.Status.GENERATED
    assert data["targets"] == payload["targets"]

    plan = MenuPlan.objects.get(id=data["plan_id"])
    assert plan.user == user
    assert plan.meals.count() == 1
    meal = plan.meals.select_related("item").first()
    assert meal is not None
    assert meal.item == menu_item
    assert pytest.approx(meal.qty, rel=1e-3) == 1.5


@pytest.mark.django_db
def test_generate_menu_marks_previous_plan_recalculated(api_client, menu_item, monkeypatch):
    payloads = [
        _make_payload(menu_item, qty=1.0, time_hint="lunch"),
        _make_payload(menu_item, qty=2.0, time_hint="dinner"),
    ]

    def fake_builder(_user):
        return copy.deepcopy(payloads.pop(0))

    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", fake_builder)

    first_resp = api_client.post("/api/nutrition/generate/", format="json")
    assert first_resp.status_code == 200

    second_resp = api_client.post("/api/nutrition/generate/", format="json")
    assert second_resp.status_code == 200

    plans = MenuPlan.objects.order_by("created_at").all()
    assert plans.count() == 2
    first_plan, second_plan = plans[0], plans[1]
    assert first_plan.status == MenuPlan.Status.RECALCULATED
    assert second_plan.status == MenuPlan.Status.GENERATED


@pytest.mark.django_db
def test_list_menu_plans_returns_history(api_client, menu_item, monkeypatch):
    payload_a = _make_payload(menu_item, qty=1.0, time_hint="breakfast")
    payload_b = _make_payload(menu_item, qty=2.5, time_hint="dinner")

    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload_a))
    api_client.post("/api/nutrition/generate/", format="json")

    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload_b))
    api_client.post("/api/nutrition/generate/", format="json")

    response = api_client.get("/api/nutrition/plans/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    most_recent = data[0]
    assert most_recent["plan_id"] != data[1]["plan_id"]
    assert most_recent["status"] == MenuPlan.Status.GENERATED
    assert "id" in most_recent["plan"][0]
    assert most_recent["plan"][0]["time_hint"] == "dinner"
    assert pytest.approx(most_recent["plan"][0]["qty"], rel=1e-3) == 2.5


@pytest.mark.django_db
def test_update_plan_status(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item, qty=1.0, time_hint="lunch")
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))

    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]

    patch_resp = api_client.patch(
        f"/api/nutrition/plans/{plan_id}/",
        {"status": "accepted"},
        format="json",
    )

    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == MenuPlan.Status.ACCEPTED

    plan = MenuPlan.objects.get(id=plan_id)
    assert plan.status == MenuPlan.Status.ACCEPTED


@pytest.mark.django_db
def test_get_single_plan(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item, qty=1.0, time_hint="lunch")
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))

    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]

    get_resp = api_client.get(f"/api/nutrition/plans/{plan_id}/")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["plan_id"] == plan_id
    assert data["plan"][0]["item_id"] == menu_item.id


@pytest.mark.django_db
def test_list_menu_plans_can_filter_by_date(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item, qty=1.0, time_hint="breakfast")
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))
    api_client.post("/api/nutrition/generate/", format="json")

    plan = MenuPlan.objects.first()
    assert plan is not None

    response = api_client.get(f"/api/nutrition/plans/?date={plan.date.isoformat()}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plan_id"] == plan.id


@pytest.mark.django_db
def test_update_plan_status_rejects_invalid_value(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item)
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))
    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]

    patch_resp = api_client.patch(
        f"/api/nutrition/plans/{plan_id}/",
        {"status": "unknown"},
        format="json",
    )

    assert patch_resp.status_code == 400
    plan = MenuPlan.objects.get(id=plan_id)
    assert plan.status == MenuPlan.Status.GENERATED


@pytest.mark.django_db
def test_update_plan_status_is_scoped_to_owner(api_client, other_user, menu_item):
    payload = _make_payload(menu_item)
    other_plan = MenuPlan.create_from_payload(user=other_user, payload=payload, plan_date=date.today())

    response = api_client.patch(
        f"/api/nutrition/plans/{other_plan.id}/",
        {"status": MenuPlan.Status.ACCEPTED},
        format="json",
    )

    assert response.status_code == 404
    other_plan.refresh_from_db()
    assert other_plan.status == MenuPlan.Status.GENERATED


@pytest.mark.django_db
def test_update_plan_meal_allows_time_and_note_changes(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item, qty=1.0, time_hint="lunch")
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))

    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]
    plan = MenuPlan.objects.prefetch_related("meals").get(id=plan_id)
    meal = plan.meals.first()
    assert meal is not None

    patch_resp = api_client.patch(
        f"/api/nutrition/plans/{plan_id}/meals/{meal.id}/",
        {"time_hint": "dinner", "user_note": "Сдвинуть позже"},
        format="json",
    )

    assert patch_resp.status_code == 200
    data = patch_resp.json()
    meal_payload = data["plan"][0]
    assert meal_payload["time_hint"] == "dinner"
    assert meal_payload["user_note"] == "Сдвинуть позже"


@pytest.mark.django_db
def test_update_plan_meal_can_replace_item(api_client, menu_item, monkeypatch):
    other_nutrients = Nutrients.objects.create(calories=420, protein=25, fat=15, carbs=45)
    other_item = MenuItem.objects.create(
        source="restaurant",
        source_id=999,
        title="Овсяная каша",
        price=210,
        nutrients=other_nutrients,
    )

    payload = _make_payload(menu_item, qty=1.0, time_hint="lunch")
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))
    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]
    meal_id = MenuPlan.objects.get(id=plan_id).meals.first().id

    patch_resp = api_client.patch(
        f"/api/nutrition/plans/{plan_id}/meals/{meal_id}/",
        {"item_id": other_item.id, "qty": 2},
        format="json",
    )

    assert patch_resp.status_code == 200
    meal_payload = patch_resp.json()["plan"][0]
    assert meal_payload["item_id"] == other_item.id
    assert pytest.approx(meal_payload["qty"], rel=1e-3) == 2


@pytest.mark.django_db
def test_update_plan_meal_validates_input(api_client, menu_item, monkeypatch):
    payload = _make_payload(menu_item)
    monkeypatch.setattr("apps.nutrition.views.build_menu_for_user", lambda u: copy.deepcopy(payload))
    resp = api_client.post("/api/nutrition/generate/", format="json")
    plan_id = resp.json()["plan_id"]
    meal_id = MenuPlan.objects.get(id=plan_id).meals.first().id

    bad_resp = api_client.patch(
        f"/api/nutrition/plans/{plan_id}/meals/{meal_id}/",
        {"qty": 0},
        format="json",
    )

    assert bad_resp.status_code == 400


@pytest.mark.django_db
def test_update_plan_meal_is_scoped_to_owner(api_client, other_user, menu_item):
    payload = _make_payload(menu_item)
    other_plan = MenuPlan.create_from_payload(user=other_user, payload=payload, plan_date=date.today())
    other_meal = other_plan.meals.first()
    assert other_meal is not None

    response = api_client.patch(
        f"/api/nutrition/plans/{other_plan.id}/meals/{other_meal.id}/",
        {"time_hint": "dinner"},
        format="json",
    )

    assert response.status_code == 404