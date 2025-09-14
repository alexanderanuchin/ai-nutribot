import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.parametrize(
    "raw",
    [
        "+7 (999) 123-45-67",
        "89991234567",
        "9991234567",
    ],
)
@pytest.mark.django_db
def test_user_can_register_and_login_with_various_phones(client, raw):
    resp = client.post("/api/users/auth/register/", {
        "phone": raw,
        "password": "StrongPass123!",
    })
    assert resp.status_code == 201
    assert User.objects.filter(username="+79991234567").exists()

    resp = client.post("/api/users/auth/token/", {
        "username": "+79991234567",
        "password": "StrongPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access" in data and "refresh" in data


@pytest.mark.django_db
def test_check_phone_endpoint(client):
    resp = client.post("/api/users/auth/check-phone/", {"phone": "+7 (999) 123-45-67"})
    assert resp.status_code == 200
    assert resp.json() == {"available": True}
    User.objects.create_user(username="+79991234567", password="StrongPass123!")
    resp = client.post("/api/users/auth/check-phone/", {"phone": "+7 (999) 123-45-67"})
    assert resp.status_code == 200
    assert resp.json() == {"available": False}


@pytest.mark.django_db
def test_weak_password_rejected(client):
    resp = client.post("/api/users/auth/register/", {
        "phone": "+7 (999) 123-45-67",
        "password": "weak",
    })
    assert resp.status_code == 400