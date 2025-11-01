import pytest

from django.urls import reverse
from rest_framework.test import APIClient

from apps.market.models import Store


@pytest.fixture
def auth_client(django_user_model):
    user = django_user_model.objects.create_user(username="pager", password="secret123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
def test_store_list_exposes_page_metadata(auth_client):
    client, user = auth_client
    for index in range(3):
        Store.objects.create(
            owner=user,
            name=f"Store {index}",
            slug=f"store-{index}",
            city="Москва",
            is_active=True,
        )

    response = client.get(reverse("market:market-store-list"), {"page_size": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["next"] is not None
    assert data["previous"] is None


@pytest.mark.django_db
def test_store_list_respects_page_parameter(auth_client):
    client, user = auth_client
    for index in range(4):
        Store.objects.create(
            owner=user,
            name=f"Paged Store {index}",
            slug=f"paged-store-{index}",
            city="Санкт-Петербург",
            is_active=True,
        )

    response = client.get(reverse("market:market-store-list"), {"page": 2, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 4
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["previous"] is not None
