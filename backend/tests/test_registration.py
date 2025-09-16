import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.parametrize(
    ("raw", "email"),
    [
        ("+7 (999) 123-45-67", "user1@example.com"),
        ("89991234567", "user2@example.com"),
        ("9991234567", "user3@example.com"),
    ],
)
@pytest.mark.django_db
def test_user_can_register_and_login_with_various_phones(client, raw, email):
    resp = client.post("/api/users/auth/register/", {
        "phone": raw,
        "email": email,
        "password": "StrongPass123!",
    })
    assert resp.status_code == 201
    user = User.objects.get(username="+79991234567")
    assert user.email == email

    resp = client.post("/api/users/auth/token/", {
        "username": "+79991234567",
        "password": "StrongPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access" in data and "refresh" in data


@pytest.mark.django_db
def test_user_can_login_with_email(client):
    resp = client.post("/api/users/auth/register/", {
        "phone": "+7 (999) 123-45-67",
        "email": "user@example.com",
        "password": "StrongPass123!",
    })
    assert resp.status_code == 201

    resp = client.post("/api/users/auth/token/", {
        "username": "user@example.com",
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
        "email": "weak@example.com",
        "password": "weak",
    })
    assert resp.status_code == 400