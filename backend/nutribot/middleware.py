from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.common.logging import summarize_header


_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id(default: str = "-") -> str:
    rid = _request_id_var.get()
    return rid or default


class RequestIDLogFilter(logging.Filter):
    """Attach the current Request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - logging
        record.request_id = get_request_id("-")
        return True


class JsonLogFormatter(logging.Formatter):
    """Simple JSON formatter that injects request id."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - logging
        base: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "rid": getattr(record, "request_id", get_request_id("-")),
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False, separators=(",", ":"))


class RequestIDMiddleware:
    """Ensure that every request has a correlation id and log safe metadata."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("audit.http")
        self.log_safe_headers = getattr(settings, "LOG_SAFE_HEADERS", True)
        self.log_request_body = getattr(settings, "LOG_REQUEST_BODY", False)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        existing = request.META.get("HTTP_X_REQUEST_ID")
        rid = existing or str(uuid.uuid4())
        token = _request_id_var.set(rid)
        request.META["HTTP_X_REQUEST_ID"] = rid
        request.request_id = rid  # type: ignore[attr-defined]

        start = time.perf_counter()
        request_snapshot: Dict[str, Any] | None = None
        if self.log_safe_headers:
            request_snapshot = self._make_request_snapshot(request)

        try:
            response = self.get_response(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            if self.log_safe_headers:
                self.logger.exception(
                    "http request failed rid=%s method=%s path=%s duration_ms=%.2f headers=%s",  # noqa: E501
                    rid,
                    request.method,
                    request.path,
                    duration_ms,
                    request_snapshot,
                    extra={"request_id": rid},
                )
            _request_id_var.reset(token)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Request-Id"] = rid

        if self.log_safe_headers:
            status = getattr(response, "status_code", "?")
            self.logger.info(
                "http request completed rid=%s method=%s path=%s status=%s duration_ms=%.2f headers=%s",  # noqa: E501
                rid,
                request.method,
                request.path,
                status,
                duration_ms,
                request_snapshot,
                extra={"request_id": rid},
            )

        _request_id_var.reset(token)
        return response

    def _make_request_snapshot(self, request: HttpRequest) -> Dict[str, Any]:
        headers = request.headers
        snapshot: Dict[str, Any] = {
            "authorization": summarize_header(headers.get("Authorization")),
            "telegram_init_data": summarize_header(headers.get("X-Telegram-Init-Data")),
            "idempotency_key": summarize_header(headers.get("Idempotency-Key")),
            "rid": request.META.get("HTTP_X_REQUEST_ID"),
        }
        if self.log_request_body and request.body:
            snapshot["body_len"] = len(request.body)
        return snapshot


__all__ = ["RequestIDMiddleware", "RequestIDLogFilter", "JsonLogFormatter", "get_request_id"]