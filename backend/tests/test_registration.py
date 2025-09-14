import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_can_register_and_login_with_phone(client):
    resp = client.post('/api/users/auth/register/', {
        'phone': '+7 (999) 123-45-67',
        'password': 'strongpass123'
    })
    assert resp.status_code == 201
    assert User.objects.filter(username='+79991234567').exists()

    resp = client.post('/api/users/auth/token/', {
        'username': '+79991234567',
        'password': 'strongpass123'
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'access' in data and 'refresh' in data