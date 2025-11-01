from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import MealPlan, MealPlanItem, Recipe
from nutribot.middleware import get_request_id

logger = logging.getLogger(__name__)


class MealPlanSubmissionSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField(min_value=1)
    servings = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        default=Decimal("1.0"),
    )


class MealPlanSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    serializer_class = MealPlanSubmissionSerializer

    def post(self, request, *args, **kwargs):  # noqa: D401 - DRF signature
        """Add, update or remove meal plan items through a simplified payload."""

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            recipe = (
                Recipe.objects.select_related("store")
                .get(pk=payload["recipe_id"], is_public=True, store__is_active=True)
            )
        except Recipe.DoesNotExist as exc:  # pragma: no cover - handled below
            raise serializers.ValidationError({"recipe_id": "Рецепт не найден или недоступен"}) from exc

        rid = getattr(request, "request_id", get_request_id())
        servings: Decimal = payload["servings"]

        with transaction.atomic():
            plan = (
                MealPlan.objects.select_for_update()
                .filter(user=request.user, is_published=False)
                .order_by("-updated_at")
                .first()
            )
            if not plan:
                plan = MealPlan.objects.create(
                    user=request.user,
                    title="Мой план питания",
                    start_date=timezone.now().date(),
                    metadata={"source": "quick-add"},
                )
            else:
                plan.metadata.setdefault("source", "quick-add")
                plan.save(update_fields=["metadata", "updated_at"])

            item_payload: dict | None = None
            status_code = status.HTTP_200_OK

            if servings <= 0:
                deleted, _ = MealPlanItem.objects.filter(meal_plan=plan, recipe=recipe).delete()
                action = "removed" if deleted else "noop"
            else:
                plan_item, created = MealPlanItem.objects.select_for_update().get_or_create(
                    meal_plan=plan,
                    recipe=recipe,
                    defaults={
                        "servings": servings,
                    },
                )
                if not created:
                    if plan_item.servings != servings:
                        plan_item.servings = servings
                        plan_item.save(update_fields=["servings"])
                    action = "updated"
                else:
                    action = "created"
                    status_code = status.HTTP_201_CREATED

                item_payload = {
                    "id": plan_item.id,
                    "recipe_id": plan_item.recipe_id,
                    "servings": float(plan_item.servings),
                }

            aggregates = plan.items.aggregate(
                items_count=Count("id"),
                total_servings=Sum("servings"),
            )
            items_count = int(aggregates.get("items_count") or 0)
            total_servings = aggregates.get("total_servings") or Decimal("0")

        logger.info(
            "market.plan.submit",
            extra={
                "rid": rid,
                "user_id": request.user.id,
                "recipe_id": recipe.id,
                "servings": float(servings),
                "action": action,
            },
        )

        response_data = {
            "status": "removed" if action == "noop" else action,
            "plan": {
                "id": plan.id,
                "title": plan.title,
                "items_count": items_count,
                "total_servings": float(total_servings),
            },
            "item": item_payload,
        }
        return Response(response_data, status=status_code)
