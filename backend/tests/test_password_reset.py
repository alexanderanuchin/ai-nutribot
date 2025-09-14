import re
import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_flow(client):
    user = User.objects.create_user(
        username="+79991234567", email="test@example.com", password="OldPass123!"
    )
    resp = client.post("/api/users/auth/password-reset/", {"email": "test@example.com"})
    assert resp.status_code == 200
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    match = re.search(r"uid=([^&]+)&token=([^\s]+)", body)
    assert match is not None
    uid, token = match.group(1), match.group(2)
    resp = client.post(
        "/api/users/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "password": "NewPass123!"},
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NewPass123!")


@pytest.mark.django_db
def test_invalid_token_rejected(client):
    user = User.objects.create_user(
        username="+79991234567", email="user@example.com", password="OldPass123!"
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    resp = client.post(
        "/api/users/auth/password-reset/confirm/",
        {"uid": uid, "token": "bad", "password": "NewPass123!"},
    )
    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.check_password("OldPass123!")