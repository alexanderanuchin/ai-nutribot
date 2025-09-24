from django.shortcuts import get_object_or_404
from rest_framework import status as drf_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import MenuPlan
from .planner import build_menu_for_user


def _serialize_meal(meal):
    item = meal.item
    nutrients = getattr(item, "nutrients", None)
    nutrients_payload = None
    if nutrients is not None:
        nutrients_payload = {
            "calories": float(nutrients.calories),
            "protein": float(nutrients.protein),
            "fat": float(nutrients.fat),
            "carbs": float(nutrients.carbs),
        }

    payload = {
        "item_id": item.id,
        "title": item.title,
        "qty": float(meal.qty),
        "time_hint": meal.time_hint,
    }

    if nutrients_payload:
        payload["nutrients"] = nutrients_payload

    if item.price is not None:
        payload["price"] = item.price

    if item.tags:
        payload["tags"] = item.tags

    return payload


def serialize_menu_plan(plan):
    return {
        "id": plan.id,
        "plan_id": plan.id,
        "date": plan.date.isoformat(),
        "created_at": plan.created_at.isoformat(),
        "status": plan.status,
        "status_display": plan.get_status_display(),
        "provider": plan.provider,
        "targets": {
            "calories": plan.target_calories,
            "protein_g": plan.target_protein,
            "fat_g": plan.target_fat,
            "carbs_g": plan.target_carbs,
        },
        "plan": [_serialize_meal(meal) for meal in plan.meals.all()],
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_menu(request):
    data = build_menu_for_user(request.user)
    plan = MenuPlan.create_from_payload(user=request.user, payload=data)

    payload = dict(data)
    payload.update(
        {
            "id": plan.id,
            "plan_id": plan.id,
            "status": plan.status,
            "status_display": plan.get_status_display(),
            "date": plan.date.isoformat(),
            "created_at": plan.created_at.isoformat(),
        }
    )

    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_menu_plans(request):
    try:
        limit = int(request.query_params.get("limit", "20"))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 90))

    plans = (
        MenuPlan.objects.filter(user=request.user)
        .order_by("-date", "-created_at")
        .prefetch_related(
            "meals__item",
            "meals__item__nutrients",
        )[:limit]
    )

    return Response([serialize_menu_plan(plan) for plan in plans])


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_plan_status(request, plan_id: int):
    raw_status = request.data.get("status")
    status_value = raw_status.strip().lower() if isinstance(raw_status, str) else None

    if status_value not in MenuPlan.Status.values:
        return Response(
            {"detail": "invalid status"},
            status=drf_status.HTTP_400_BAD_REQUEST,
        )

    plan = get_object_or_404(
        MenuPlan.objects.filter(user=request.user)
        .prefetch_related("meals__item", "meals__item__nutrients"),
        id=plan_id,
    )

    plan.status = status_value
    plan.save(update_fields=["status"])

    return Response(serialize_menu_plan(plan))


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok"})
