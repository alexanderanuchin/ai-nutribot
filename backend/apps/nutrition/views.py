from datetime import datetime

from django.shortcuts import get_object_or_404
from rest_framework import status as drf_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import MenuItem

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
        "id": meal.id,
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

    if meal.user_note:
        payload["user_note"] = meal.user_note

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

    date_param = request.query_params.get("date")
    date_filter = None
    if isinstance(date_param, str) and date_param:
        try:
            date_filter = datetime.fromisoformat(date_param).date()
        except ValueError:
            date_filter = None

    plans = (
        MenuPlan.objects.filter(user=request.user)
        .filter(**({"date": date_filter} if date_filter else {}))
        .order_by("-date", "-created_at")
        .prefetch_related(
            "meals__item",
            "meals__item__nutrients",
        )[:limit]
    )

    return Response([serialize_menu_plan(plan) for plan in plans])


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def plan_detail(request, plan_id: int):
    plan = get_object_or_404(
        MenuPlan.objects.filter(user=request.user)
        .prefetch_related("meals__item", "meals__item__nutrients"),
        id=plan_id,
    )

    if request.method == "GET":
        return Response(serialize_menu_plan(plan))

    raw_status = request.data.get("status")
    status_value = raw_status.strip().lower() if isinstance(raw_status, str) else None

    if status_value not in MenuPlan.Status.values:
        return Response(
            {"detail": "invalid status"},
            status=drf_status.HTTP_400_BAD_REQUEST,
        )

    plan.status = status_value
    plan.save(update_fields=["status"])

    return Response(serialize_menu_plan(plan))


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_plan_meal(request, plan_id: int, meal_id: int):
    plan = get_object_or_404(MenuPlan.objects.filter(user=request.user), id=plan_id)

    meal = get_object_or_404(
        plan.meals.select_related("item", "item__nutrients"),
        id=meal_id,
    )

    data = request.data or {}
    updates: dict[str, object] = {}

    if "qty" in data:
        qty = data.get("qty")
        try:
            qty_value = float(qty)
        except (TypeError, ValueError):
            return Response({"detail": "invalid qty"}, status=drf_status.HTTP_400_BAD_REQUEST)
        if qty_value <= 0:
            return Response({"detail": "invalid qty"}, status=drf_status.HTTP_400_BAD_REQUEST)
        updates["qty"] = qty_value

    if "time_hint" in data:
        time_hint = data.get("time_hint")
        if not isinstance(time_hint, str) or not time_hint.strip():
            return Response({"detail": "invalid time_hint"}, status=drf_status.HTTP_400_BAD_REQUEST)
        updates["time_hint"] = time_hint.strip()

    if "user_note" in data:
        note = data.get("user_note")
        if note is None:
            updates["user_note"] = ""
        elif not isinstance(note, str):
            return Response({"detail": "invalid user_note"}, status=drf_status.HTTP_400_BAD_REQUEST)
        else:
            updates["user_note"] = note.strip()

    if "item_id" in data:
        item_id = data.get("item_id")
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError):
            return Response({"detail": "invalid item_id"}, status=drf_status.HTTP_400_BAD_REQUEST)
        item = get_object_or_404(MenuItem.objects.filter(is_available=True), id=item_id_int)
        updates["item"] = item

    if not updates:
        return Response({"detail": "no changes supplied"}, status=drf_status.HTTP_400_BAD_REQUEST)

    for field, value in updates.items():
        setattr(meal, field, value)
    meal.save()

    refreshed_plan = (
        MenuPlan.objects.filter(id=plan.id, user=request.user)
        .prefetch_related("meals__item", "meals__item__nutrients")
        .get()
    )

    return Response(serialize_menu_plan(refreshed_plan))


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"status": "ok"})
