from __future__ import annotations

from django.urls import path

from .views import RemoteApplicationLogView

app_name = "monitoring"

urlpatterns = [
    path(
        "application/logs/",
        RemoteApplicationLogView.as_view(),
        name="application-log-ingest",
    ),
]


__all__ = ["urlpatterns"]