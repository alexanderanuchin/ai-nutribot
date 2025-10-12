from __future__ import annotations

from typing import Any, Dict, Iterable, List

from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasBotKeyOrIsAuthenticated

from .models import ApplicationLog
from .serializers import RemoteApplicationLogSerializer


class RemoteApplicationLogView(APIView):
    permission_classes = [HasBotKeyOrIsAuthenticated]

    def post(self, request, *args, **kwargs):  # pragma: no cover - integration thin wrapper
        data = request.data
        if isinstance(data, dict) and "entries" in data:
            entries = data["entries"]
            many = True
        else:
            entries = data
            many = isinstance(data, list)

        serializer = RemoteApplicationLogSerializer(data=entries, many=many)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        if not isinstance(validated, list):
            validated_entries: Iterable[Dict[str, Any]] = [validated]
        else:
            validated_entries = validated

        default_component = getattr(request, "_auth_component", "external") or "external"
        default_logger = {
            "bot": "bot.monitoring",
            "webapp": "webapp.monitoring",
        }.get(default_component, "external.monitoring")

        base_serializer: RemoteApplicationLogSerializer
        if isinstance(serializer, serializers.ListSerializer):
            base_serializer = serializer.child  # type: ignore[assignment]
        else:
            base_serializer = serializer  # type: ignore[assignment]

        created_entries: List[ApplicationLog] = []
        for entry in validated_entries:
            payload = base_serializer.build_payload(
                entry,
                default_logger=default_logger,
                default_component=default_component,
            )
            if not payload.get("request_id"):
                header_rid = request.META.get("HTTP_X_REQUEST_ID") or ""
                payload["request_id"] = header_rid
            created_entries.append(ApplicationLog.objects.create(**payload))

        ids = [entry.pk for entry in created_entries]
        return Response(
            {"created": len(ids), "ids": ids},
            status=status.HTTP_201_CREATED,
        )


__all__ = ["RemoteApplicationLogView"]