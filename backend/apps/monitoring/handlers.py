from __future__ import annotations

import logging
import traceback
from typing import Any, Dict

from django.apps import apps
from django.conf import settings
from django.db import DatabaseError, OperationalError

from nutribot.middleware import get_request_id

APPLICATION_GROUP = "application"
ADMIN_GROUP = "administrative"


class DatabaseLogHandler(logging.Handler):
    """Persist structured log messages for later inspection in the admin."""

    def __init__(self, capacity: int | None = None, prune_batch: int = 200, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.capacity = capacity or getattr(settings, "LOG_DB_CAPACITY", 5000)
        self.prune_batch = prune_batch

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - heavy IO guarded in tests
        if getattr(record, "skip_db_logging", False):
            return
        if not apps.ready:
            return
        try:
            ApplicationLog = apps.get_model("monitoring", "ApplicationLog")
        except LookupError:
            return
        if ApplicationLog is None:
            return

        payload = self._build_payload(record)

        try:
            entry = ApplicationLog.objects.create(**payload)
        except (OperationalError, DatabaseError):
            return

        if not self.capacity:
            return

        if entry.pk % self.prune_batch == 0:
            overflow = (
                ApplicationLog.objects.order_by("-pk").values_list("pk", flat=True)[self.capacity:]
            )
            if overflow:
                ApplicationLog.objects.filter(pk__in=list(overflow)).delete()

    def _build_payload(self, record: logging.LogRecord) -> Dict[str, Any]:
        message = record.getMessage()
        request_id = getattr(record, "request_id", get_request_id("-"))
        extra: Dict[str, Any] = {
            "pathname": record.pathname,
            "func": record.funcName,
            "line": record.lineno,
        }
        for key in ("user_id", "order_id", "task_id"):
            if hasattr(record, key):
                extra[key] = getattr(record, key)
        exc_text = ""
        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info))
        return {
            "level": record.levelname,
            "logger_name": record.name,
            "message": message[:4096],
            "request_id": request_id,
            "group": self._resolve_group(record),
            "extra": extra,
            "exc_text": exc_text[:8192],
        }

    def _resolve_group(self, record: logging.LogRecord) -> str:
        logger_name = record.name or ""
        admin_names = getattr(settings, "LOG_ADMIN_LOGGER_NAMES", ())
        admin_prefixes = getattr(settings, "LOG_ADMIN_LOGGER_PREFIXES", ("audit.",))

        if logger_name in admin_names:
            return ADMIN_GROUP

        for prefix in admin_prefixes:
            if logger_name.startswith(prefix):
                return ADMIN_GROUP

        return APPLICATION_GROUP


__all__ = ["DatabaseLogHandler"]
