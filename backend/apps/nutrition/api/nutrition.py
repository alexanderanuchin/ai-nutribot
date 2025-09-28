"""REST endpoints for nutrition plans."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, Dict, Mapping
from uuid import uuid4

from celery.result import AsyncResult
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.nutrition.models import MenuPlan, PlanMeal
from apps.nutrition.serializers.nutrition import (
    MenuPlanGenerateSerializer,
    MenuPlanRegenerateSerializer,
)
from apps.nutrition.services.menu_plan_service import (
    MenuPlanEngineError,
    MenuPlanPermissionError,
    MenuPlanService,
    MenuPlanValidationError,
)
from apps.nutrition.tasks import generate_menu_task

_service = MenuPlanService()


def _serialize_summary(plan: MenuPlan) -> Dict[str, Any]:
    snapshot = getattr(plan, "snapshot", None)
    if snapshot and snapshot.summary:
        return snapshot.summary

    meals = list(plan.meals.select_related("item"))
    total_cost = Decimal("0.00")
    unique_items = set()
    for meal in meals:
        unique_items.add(meal.item_id)
        price = getattr(meal.item, "price", 0) or 0
        qty = Decimal(str(meal.qty or 0))
        total_cost += Decimal(price) * qty

    period_days = 1
    if snapshot and snapshot.metadata:
        request_meta = snapshot.metadata.get("request") or {}
        period_days = int(request_meta.get("period_days") or 1)

    return {
        "period_days": period_days,
        "daily_kcal": plan.target_calories,
        "protein_g": plan.target_protein,
        "fat_g": plan.target_fat,
        "carbs_g": plan.target_carbs,
        "meals_total": len(meals),
        "unique_dishes": len(unique_items),
        "estimated_cost_rub_per_day": _format_decimal(total_cost / Decimal(max(1, period_days))),
        "notes": "engine=hybrid; fallback=unknown",
    }


def _format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _serialize_plan(plan: MenuPlan) -> Dict[str, Any]:
    return {
        "plan_id": plan.id,
        "status": plan.status,
        "created_at": plan.created_at.isoformat(),
        "summary": _serialize_summary(plan),
    }


def _sanitize_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(params, sort_keys=True, default=str))


def _build_job_id(user_id: int, params: Mapping[str, Any]) -> str:
    fingerprint = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    period = params.get("period_days", "?")
    return f"user:{user_id}:generate:{period}:{fingerprint}"[:120]


def _schedule_generation_job(user, params: Mapping[str, Any]) -> str:
    payload = _sanitize_params(params)
    job_id = _build_job_id(user.id, payload)
    existing = AsyncResult(job_id)
    state = existing.state

    backend_state = None
    try:
        meta = existing.backend.get_task_meta(job_id)
    except Exception:  # pragma: no cover - defensive against backend errors
        meta = None
    if meta and isinstance(meta, Mapping):
        backend_state = meta.get("status")

    if state in {"STARTED", "RETRY"} or backend_state in {"STARTED", "RETRY"}:
        return job_id

    if existing.ready():
        if existing.successful() or backend_state == "SUCCESS":
            return job_id
        state = state or backend_state

    if state == "FAILURE" or backend_state == "FAILURE":
        job_id = f"{job_id}:retry:{uuid4().hex[:8]}"

    generate_menu_task.apply_async(
        kwargs={"user_id": user.id, "params": payload, "context": {"mode": "async"}},
        task_id=job_id,
    )
    return job_id


def _check_job_permission(job_id: str, user_id: int) -> bool:
    return job_id.startswith(f"user:{user_id}:")


class GenerateAndSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MenuPlanGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        should_run_sync = params.get("period_days", 7) <= 7
        if should_run_sync:
            try:
                plan, summary = _service.generate_and_save(user=request.user, params=params)
            except MenuPlanValidationError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except MenuPlanEngineError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"plan_id": plan.id, "status": plan.status, "summary": summary})

        job_id = _schedule_generation_job(request.user, params)
        return Response({"job_id": job_id}, status=status.HTTP_202_ACCEPTED)


class JobStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: str):
        if not _check_job_permission(job_id, request.user.id):
            return Response({"detail": "job not found"}, status=status.HTTP_404_NOT_FOUND)

        result = AsyncResult(job_id)
        state = result.state
        if state in {"PENDING", "STARTED", "RETRY"}:
            return Response({"status": "pending"})
        if state == "FAILURE":
            error_message = str(result.result)
            return Response({"status": "failed", "error": error_message})
        payload = result.result or {}
        summary = payload.get("summary")
        response = {
            "status": "done",
            "plan_id": payload.get("plan_id"),
        }
        if summary:
            response["summary"] = summary
        return Response(response)


class LatestPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = (
            MenuPlan.objects.filter(user=request.user)
            .select_related("snapshot")
            .prefetch_related(Prefetch("meals", queryset=plan_meals_queryset()))
            .order_by("-created_at")
            .first()
        )
        if not plan:
            return Response({"detail": "no plans"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_plan(plan))


def plan_meals_queryset():
    return PlanMeal.objects.select_related("item")


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))
        plans = (
            MenuPlan.objects.filter(user=request.user)
            .select_related("snapshot")
            .prefetch_related(Prefetch("meals", queryset=plan_meals_queryset()))
            .order_by("-created_at")[:limit]
        )
        return Response([_serialize_plan(plan) for plan in plans])


class AcceptPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id: int):
        try:
            plan = _service.accept_plan(user=request.user, plan_id=plan_id)
        except MenuPlanPermissionError:
            return Response({"detail": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_plan(plan))


class RejectPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id: int):
        try:
            plan = _service.reject_plan(user=request.user, plan_id=plan_id)
        except MenuPlanPermissionError:
            return Response({"detail": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_plan(plan))


class RegeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id: int):
        serializer = MenuPlanRegenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        overrides = serializer.validated_data.get("overrides")
        try:
            plan, summary = _service.regenerate_plan(user=request.user, plan_id=plan_id, overrides=overrides)
        except MenuPlanPermissionError:
            return Response({"detail": "plan not found"}, status=status.HTTP_404_NOT_FOUND)
        except MenuPlanValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except MenuPlanEngineError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"plan_id": plan.id, "status": plan.status, "summary": summary})