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
        "password": "strongpass123",
    })
    assert resp.status_code == 201
    assert User.objects.filter(username="+79991234567").exists()

    resp = client.post("/api/users/auth/token/", {
        "username": "+79991234567",
        "password": "strongpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access" in data and "refresh" in data