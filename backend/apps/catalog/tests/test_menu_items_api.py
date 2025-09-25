import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalog.models import MenuItem, Nutrients, Restaurant


@pytest.fixture
def api_client(db):
    client = APIClient()
    User = get_user_model()
    user = User.objects.create_user(username="user@example.com", password="StrongPass123")
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def menu_items(db):
    restaurant = Restaurant.objects.create(name="Test", city="City")
    items = []
    for idx in range(1, 5):
        nutrients = Nutrients.objects.create(calories=400 + idx, protein=25, fat=12, carbs=40)
        items.append(
            MenuItem.objects.create(
                source="restaurant",
                source_id=restaurant.id,
                title=f"Блюдо {idx}",
                price=100 + idx,
                nutrients=nutrients,
            )
        )
    return items


@pytest.mark.django_db
def test_menu_items_support_search(api_client, menu_items):
    response = api_client.get("/api/catalog/items/?search=Блюдо 2")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["title"].endswith("2")


@pytest.mark.django_db
def test_menu_items_limit(api_client, menu_items):
    response = api_client.get("/api/catalog/items/?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2