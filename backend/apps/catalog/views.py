from __future__ import annotations

from django.conf import settings

from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.nutrition.menu_filters import MenuFilterService

from .models import MenuItem
from .serializers import MenuItemSerializer


def _get_minimum_available_items() -> int:
    try:
        return max(1, int(getattr(settings, "CATALOG_MINIMUM_AVAILABLE_ITEMS", 120)))
    except (TypeError, ValueError):
        return 120


class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(["GET"])
@permission_classes([AllowAny])
def catalog_health(request):
    minimum_required = _get_minimum_available_items()

    available_qs = MenuItem.objects.filter(is_available=True)
    available_count = available_qs.count()
    total_count = MenuItem.objects.count()

    filter_service = MenuFilterService()
    filters_ok = True
    filters_error: str | None = None

    try:
        filtered_items = filter_service.filter()
    except Exception as exc:  # pragma: no cover - defensive
        filtered_items = []
        filters_ok = False
        filters_error = str(exc)

    limit = filter_service.limit
    filtered_count = len(filtered_items)
    required_for_front = min(minimum_required, limit)
    has_sufficient_items = filtered_count >= required_for_front
    is_truncated = filtered_count >= limit

    empty_filters_ok = True
    if filters_ok:
        try:
            empty_result = filter_service.filter(
                city="__nonexistent__",
                allergies=["unlikely"],
                exclusions=["unlikely"],
                budget=1,
            )
            empty_filters_ok = empty_result == []
        except Exception as exc:  # pragma: no cover - defensive
            empty_filters_ok = False
            filters_error = str(exc)

    status = "ok"
    if available_count < minimum_required or not filters_ok or not empty_filters_ok or not has_sufficient_items:
        status = "degraded"

    payload = {
        "status": status,
        "totals": {
            "items": total_count,
            "available": available_count,
        },
        "limits": {
            "minimum_required": minimum_required,
            "filter_limit": limit,
            "filtered_count": filtered_count,
            "is_truncated": is_truncated,
            "has_sufficient_items": has_sufficient_items,
        },
        "filters": {
            "filters_ok": filters_ok,
            "empty_result_ok": empty_filters_ok,
            "error": filters_error,
        },
    }

    return Response(payload)
