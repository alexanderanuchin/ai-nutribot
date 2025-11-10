from __future__ import annotations

import time
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import connections
from django.core.cache import caches

# Optional: django-prometheus export (fallback to no-op if not installed)
try:
    from django_prometheus.exports import ExportToDjangoView  # type: ignore
except Exception:  # pragma: no cover
    ExportToDjangoView = None  # type: ignore


def _json_ok(payload: Dict[str, Any], status: int = 200) -> JsonResponse:
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe: the process is up and can serve requests."""
    return _json_ok(
        {
            "status": "ok",
            "service": "nutribot-backend",
            "timestamp": int(time.time()),
        }
    )


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness probe: verify we can reach critical dependencies (DB, cache)."""
    start = time.monotonic()
    checks: Dict[str, Any] = {}
    ok = True

    # Database
    try:
        for alias in connections:
            conn = connections[alias]
            conn.ensure_connection()
        checks["db"] = "ok"
    except Exception as exc:  # pragma: no cover
        ok = False
        checks["db"] = f"error: {exc.__class__.__name__}"

    # Cache (optional)
    try:
        default_cache = caches["default"]
        probe_key = "readyz:probe"
        default_cache.set(probe_key, "1", timeout=5)
        default_cache.get(probe_key)
        checks["cache"] = "ok"
    except Exception as exc:  # pragma: no cover
        # Cache is not critical – mark as warning, do not fail overall readiness.
        checks["cache"] = f"warn: {exc.__class__.__name__}"

    checks["duration_ms"] = int((time.monotonic() - start) * 1000)
    status = 200 if ok else 503
    return _json_ok({"status": "ok" if ok else "error", **checks}, status=status)


def metrics(request: HttpRequest) -> HttpResponse:
    """Prometheus metrics endpoint.
    We map both /metrics and /metrics/ in urls.py and support environments without django_prometheus.
    """
    if ExportToDjangoView is not None:
        # Delegate to django-prometheus exporter (it sets the correct content-type and caching headers)
        return ExportToDjangoView(request)
    # Fallback: minimal body to keep scrapers alive (won't expose metrics)
    body = b"# metrics exporter is not installed\n"
    response = HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response
