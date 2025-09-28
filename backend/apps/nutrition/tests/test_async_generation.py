import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutribot.settings")

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(username="async@example.com", password="StrongPass123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class _DummyBackend:
    def __init__(self, status: str = "PENDING"):
        self._status = status

    def get_task_meta(self, task_id: str):
        return {"status": self._status, "result": None, "task_id": task_id}


class _DummyAsyncResult:
    def __init__(
        self,
        task_id: str,
        *,
        state: str = "PENDING",
        ready: bool = False,
        successful: bool = False,
        backend_status: str | None = None,
    ):
        self.id = task_id
        self.state = state
        self._ready = ready
        self._successful = successful
        status = backend_status if backend_status is not None else state
        self._backend = _DummyBackend(status or "PENDING")

    def ready(self) -> bool:
        return self._ready

    def successful(self) -> bool:
        return self._successful

    @property
    def backend(self):
        return self._backend


@pytest.mark.django_db
def test_generate_and_save_async_enqueues_job(api_client, user, monkeypatch):
    calls = []

    def fake_apply_async(*args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "apps.nutrition.api.nutrition.generate_menu_task.apply_async", fake_apply_async
    )

    monkeypatch.setattr(
        "apps.nutrition.api.nutrition.AsyncResult",
        lambda task_id: _DummyAsyncResult(task_id, state="PENDING", ready=False, successful=False),
    )

    payload = {"period_days": 10}
    response = api_client.post("/api/nutrition/generate_and_save/", payload, format="json")

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert job_id
    assert len(calls) == 1

    kwargs = calls[0]["kwargs"]
    assert kwargs["user_id"] == user.id
    assert kwargs["params"]["period_days"] == 10
    assert calls[0]["task_id"] == job_id