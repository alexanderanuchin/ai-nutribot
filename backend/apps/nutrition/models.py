from datetime import date as dt_date

from django.db import models, transaction
from django.conf import settings
from apps.catalog.models import MenuItem


class MenuPlan(models.Model):
    class Status(models.TextChoices):
        GENERATED = "generated", "Сгенерирован"
        ACCEPTED = "accepted", "Принят"
        REJECTED = "rejected", "Отклонён"
        RECALCULATED = "recalculated", "Пересчитан"
        PROCESSING = "processing", "В обработке"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    target_calories = models.IntegerField()
    target_protein = models.IntegerField()
    target_fat = models.IntegerField()
    target_carbs = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=32, default="hybrid")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.GENERATED,
    )

    @classmethod
    def create_from_payload(
        cls,
        *,
        user,
        payload: dict,
        plan_date: dt_date | None = None,
        provider: str = "hybrid",
    ):
        plan_date = plan_date or dt_date.today()

        targets = payload.get("targets") or {}
        required_keys = {"calories", "protein_g", "fat_g", "carbs_g"}
        if not required_keys.issubset(targets):
            raise ValueError("payload targets missing required keys")

        plan_items = payload.get("plan") or []

        with transaction.atomic():
            plan = cls.objects.create(
                user=user,
                date=plan_date,
                target_calories=int(targets.get("calories") or 0),
                target_protein=int(targets.get("protein_g") or 0),
                target_fat=int(targets.get("fat_g") or 0),
                target_carbs=int(targets.get("carbs_g") or 0),
                provider=provider,
            )

            (
                cls.objects.filter(user=user, date=plan_date)
                .exclude(id=plan.id)
                .filter(status=cls.Status.GENERATED)
                .update(status=cls.Status.RECALCULATED)
            )

            item_ids = [entry.get("item_id") for entry in plan_items if entry.get("item_id")]
            items_map = {
                item.id: item for item in MenuItem.objects.filter(id__in=item_ids)
            }

            meals_to_create = []
            for entry in plan_items:
                item = items_map.get(entry.get("item_id"))
                if not item:
                    continue

                qty_raw = entry.get("qty", 1)
                try:
                    qty = float(qty_raw)
                except (TypeError, ValueError):
                    qty = 1.0
                if qty <= 0:
                    continue

                time_hint = entry.get("time_hint") or "any"
                if not isinstance(time_hint, str):
                    time_hint = "any"

                meals_to_create.append(
                    PlanMeal(
                        plan=plan,
                        item=item,
                        qty=qty,
                        time_hint=time_hint,
                    )
                )

            if meals_to_create:
                PlanMeal.objects.bulk_create(meals_to_create)

        return plan


class PlanMeal(models.Model):
    plan = models.ForeignKey(MenuPlan, on_delete=models.CASCADE, related_name="meals")
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    qty = models.FloatField(default=1.0)
    time_hint = models.CharField(max_length=16, default="any")
    user_note = models.TextField(blank=True, default="")
