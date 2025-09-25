from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import MenuItem, Nutrients, Restaurant


@pytest.fixture

def api_client() -> APIClient:
    return APIClient()


def _create_item(*, restaurant: Restaurant, title: str = "Блюдо", price: int = 350) -> MenuItem:
    nutrients = Nutrients.objects.create(calories=500, protein=30, fat=20, carbs=40)
    return MenuItem.objects.create(
        source="restaurant",
        source_id=restaurant.id,
        title=title,
        price=price,
        nutrients=nutrients,
    )


@pytest.mark.django_db

def test_catalog_health_reports_ok(api_client: APIClient, settings):
    settings.CATALOG_MINIMUM_AVAILABLE_ITEMS = 2
    restaurant = Restaurant.objects.create(name="Cafe", city="Москва", is_active=True)
    _create_item(restaurant=restaurant, title="Боул")
    _create_item(restaurant=restaurant, title="Салат")

    response = api_client.get("/api/catalog/health/")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["totals"]["available"] == 2
    assert payload["limits"]["has_sufficient_items"] is True
    assert payload["filters"]["empty_result_ok"] is True


@pytest.mark.django_db

def test_catalog_health_degraded_when_not_enough_items(api_client: APIClient, settings):
    settings.CATALOG_MINIMUM_AVAILABLE_ITEMS = 3
    restaurant = Restaurant.objects.create(name="Cafe", city="Москва", is_active=True)
    _create_item(restaurant=restaurant, title="Боул")

    response = api_client.get("/api/catalog/health/")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "degraded"
    assert payload["totals"]["available"] == 1
    assert payload["limits"]["has_sufficient_items"] is False
    assert payload["filters"]["filters_ok"] is True