import logging

import pytest

from django.urls import reverse

from apps.monitoring.handlers import DatabaseLogHandler
from apps.monitoring.models import ApplicationLog


@pytest.mark.django_db
def test_database_log_handler_persists_log_record():
    handler = DatabaseLogHandler(capacity=10)
    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=42,
        msg="processing failed for %s",
        args=("order-1",),
        exc_info=None,
        func="handle",
    )
    record.request_id = "RID-123"

    handler.emit(record)

    entry = ApplicationLog.objects.get()
    assert entry.level == "ERROR"
    assert entry.logger_name == "test.logger"
    assert entry.message == "processing failed for order-1"
    assert entry.request_id == "RID-123"
    assert entry.extra["func"] == "handle"
    assert entry.group == ApplicationLog.Group.APPLICATION


@pytest.mark.django_db
def test_database_log_handler_marks_admin_group(settings):
    settings.LOG_ADMIN_LOGGER_PREFIXES = ("audit.",)
    handler = DatabaseLogHandler(capacity=10)
    record = logging.LogRecord(
        name="audit.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=84,
        msg="admin task completed",
        args=(),
        exc_info=None,
        func="admin_task",
    )

    handler.emit(record)

    entry = ApplicationLog.objects.get()
    assert entry.group == ApplicationLog.Group.ADMINISTRATIVE


@pytest.mark.django_db
def test_stream_view_filters_by_after(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    client.force_login(user)

    first = ApplicationLog.objects.create(
        level="INFO",
        logger_name="demo",
        message="first",
    )
    second = ApplicationLog.objects.create(
        level="WARNING",
        logger_name="demo",
        message="second",
    )

    response = client.get(
        reverse("admin:monitoring_applicationlog_stream"),
        {"after": first.pk},
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["results"]] == [second.pk]


@pytest.mark.django_db
def test_stream_view_filters_by_group(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    client.force_login(user)

    ApplicationLog.objects.create(
        level="INFO",
        logger_name="service",
        message="application",
        group=ApplicationLog.Group.APPLICATION,
    )
    admin_log = ApplicationLog.objects.create(
        level="WARNING",
        logger_name="audit.http",
        message="admin",
        group=ApplicationLog.Group.ADMINISTRATIVE,
    )

    response = client.get(
        reverse("admin:monitoring_applicationlog_stream"),
        {"group": ApplicationLog.Group.ADMINISTRATIVE},
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data["results"]] == [admin_log.pk]
    assert data["results"][0]["group"] == ApplicationLog.Group.ADMINISTRATIVE