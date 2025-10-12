from __future__ import annotations

from typing import Any, Dict

from django.utils import timezone
from rest_framework import serializers

from .models import ApplicationLog


class RemoteApplicationLogSerializer(serializers.Serializer):
    level = serializers.CharField()
    message = serializers.CharField()
    logger = serializers.CharField(max_length=255, required=False, allow_blank=True)
    request_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    group = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(child=serializers.JSONField(), required=False)
    exc_text = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(required=False)
    component = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_level(self, value: str) -> str:
        normalized = (value or "").upper()
        if normalized not in ApplicationLog.Level.values:
            raise serializers.ValidationError("Unsupported log level")
        return normalized

    def validate_group(self, value: str) -> str:
        if not value:
            return ApplicationLog.Group.APPLICATION
        if value not in ApplicationLog.Group.values:
            raise serializers.ValidationError("Unsupported log group")
        return value

    def build_payload(
        self,
        data: Dict[str, Any],
        *,
        default_logger: str,
        default_component: str,
    ) -> Dict[str, Any]:
        message = data["message"][:4096]
        level = (data.get("level") or ApplicationLog.Level.INFO).upper()
        if level not in ApplicationLog.Level.values:
            level = ApplicationLog.Level.INFO
        logger_name = data.get("logger") or default_logger
        group = data.get("group") or ApplicationLog.Group.APPLICATION
        if group not in ApplicationLog.Group.values:
            group = ApplicationLog.Group.APPLICATION
        request_id = data.get("request_id") or ""
        exc_text = (data.get("exc_text") or "")[:8192]
        extra = data.get("extra") or {}
        component = data.get("component") or default_component
        if component and isinstance(extra, dict) and "component" not in extra:
            extra = {**extra, "component": component}

        payload: Dict[str, Any] = {
            "level": level,
            "message": message,
            "logger_name": logger_name,
            "group": group,
            "request_id": request_id,
            "extra": extra,
            "exc_text": exc_text,
        }

        timestamp = data.get("timestamp")
        if timestamp is not None:
            payload["created_at"] = timestamp
        else:
            payload.setdefault("created_at", timezone.now())

        return payload


__all__ = ["RemoteApplicationLogSerializer"]