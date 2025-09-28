"""High-level service orchestrating nutrition plan generation and lifecycle."""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import MenuItem
from apps.nutrition.menu_filters import MenuFilterService
from apps.nutrition.menu_selection import MenuSelectionService
from apps.nutrition.models import MenuPlan, MenuPlanSnapshot
from apps.nutrition.services import Targets, tdee
from apps.users.models import Profile

User = get_user_model()

logger = logging.getLogger("nutribot.nutrition")


class MenuPlanServiceError(RuntimeError):
    """Base exception for the high-level menu plan service."""


class MenuPlanValidationError(MenuPlanServiceError):
    """Raised when the provided parameters are invalid."""


class MenuPlanEngineError(MenuPlanServiceError):
    """Raised when the menu composition engine fails to produce a plan."""


class MenuPlanPermissionError(MenuPlanServiceError):
    """Raised when the user attempts to access someone else's plan."""


@dataclass(slots=True)
class NormalizedParams:
    period_days: int
    target_calories: int
    targets: Targets
    budget: Optional[Decimal]
    variety: float
    meal_times: List[str]
    allergies: List[str]
    exclusions: List[str]
    city: Optional[str]
    constraints: Dict[str, Any]
    goal: str
    overrides: Dict[str, Any]
    raw_request: Dict[str, Any]


def _decimal_two_places(value: Decimal | int | float | None) -> str:
    decimal_value = Decimal(value or 0)
    quantized = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _merge_unique(base: Sequence[str], extra: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    merged: List[str] = []
    for container in (base, extra):
        for value in container:
            if not value:
                continue
            normalized = str(value).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class _FallbackRecorder:
    def __init__(self, base_strategy):
        self._base = base_strategy
        self.used = False

    def __call__(self, items: Sequence[MenuItem], targets: Targets):
        self.used = True
        return self._base(items, targets)


class MenuPlanService:
    """Facade that wraps the existing menu engine with persistence and metadata."""

    def __init__(
        self,
        *,
        filter_service: MenuFilterService | None = None,
        selection_service: MenuSelectionService | None = None,
    ) -> None:
        self._filter_service = filter_service or MenuFilterService()
        self._selection_proto = selection_service or MenuSelectionService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_and_save(
        self,
        *,
        user: User,
        params: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> Tuple[MenuPlan, Dict[str, Any]]:
        """Generate a nutrition plan and persist it alongside metadata."""

        if not hasattr(user, "profile"):
            raise MenuPlanValidationError("user profile is missing")

        normalized = self._normalize_params(user.profile, params)
        fingerprint = self._fingerprint(user.id, normalized.raw_request, context)

        existing = (
            MenuPlanSnapshot.objects.select_related("plan")
            .filter(plan__user=user, metadata__fingerprint=fingerprint)
            .order_by("-plan__created_at")
            .first()
        )
        if existing:
            plan = existing.plan
            logger.info(
                "plan_generate_requested", extra={"user_id": user.id, "plan_id": plan.id, "reused": True}
            )
            return plan, existing.summary

        logger.info(
            "plan_generate_requested",
            extra={
                "user_id": user.id,
                "period_days": normalized.period_days,
                "variety": normalized.variety,
            },
        )

        payload, summary, metadata = self._build_plan_payload(user, normalized)

        with transaction.atomic():
            plan = MenuPlan.create_from_payload(
                user=user,
                payload=payload,
                plan_date=date.today(),
                provider="hybrid",
            )
            plan.status = MenuPlan.Status.GENERATED
            plan.save(update_fields=["status"])
            MenuPlanSnapshot.objects.update_or_create(
                plan=plan,
                defaults={
                    "summary": summary,
                    "metadata": metadata | {"fingerprint": fingerprint},
                },
            )

        logger.info(
            "plan_generated",
            extra={
                "user_id": user.id,
                "plan_id": plan.id,
                "fallback": metadata.get("fallback_used", False),
            },
        )
        return plan, summary

    def accept_plan(self, *, user: User, plan_id: int) -> MenuPlan:
        plan = self._get_user_plan(user, plan_id)
        plan.status = MenuPlan.Status.ACCEPTED
        plan.save(update_fields=["status"])
        logger.info("plan_accepted", extra={"user_id": user.id, "plan_id": plan.id})
        return plan

    def reject_plan(self, *, user: User, plan_id: int) -> MenuPlan:
        plan = self._get_user_plan(user, plan_id)
        plan.status = MenuPlan.Status.REJECTED
        plan.save(update_fields=["status"])
        logger.info("plan_rejected", extra={"user_id": user.id, "plan_id": plan.id})
        return plan

    def regenerate_plan(
        self,
        *,
        user: User,
        plan_id: int,
        overrides: Mapping[str, Any] | None = None,
    ) -> Tuple[MenuPlan, Dict[str, Any]]:
        plan = self._get_user_plan(user, plan_id)
        snapshot = getattr(plan, "snapshot", None)
        if snapshot is None or not snapshot.metadata:
            raise MenuPlanValidationError("cannot regenerate plan without metadata")

        base_request = snapshot.metadata.get("request")
        if not isinstance(base_request, dict):
            raise MenuPlanValidationError("original request payload missing")

        merged = json.loads(json.dumps(base_request))
        if overrides:
            merged.setdefault("overrides", {})
            overrides_dict = merged["overrides"]
            for key, value in overrides.items():
                if key == "target_calories":
                    merged["target_calories"] = value
                else:
                    overrides_dict[key] = value
        return self.generate_and_save(user=user, params=merged, context={"regenerated_from": plan_id})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_params(self, profile: Profile, params: Mapping[str, Any]) -> NormalizedParams:
        raw_overrides = params.get("overrides") or {}
        if not isinstance(raw_overrides, Mapping):
            raise MenuPlanValidationError("overrides must be a mapping")

        try:
            period_days = int(params.get("period_days", 7))
        except (TypeError, ValueError):
            raise MenuPlanValidationError("period_days must be an integer")
        if period_days < 1 or period_days > 30:
            raise MenuPlanValidationError("period_days must be between 1 and 30")

        goal_override = str(raw_overrides.get("goals") or "").strip() or None
        goal_value = self._map_goal(goal_override, profile.goal)

        profile_weight = _as_float(profile.weight_kg, default=70.0)
        profile_height = int(getattr(profile, "height_cm", 170) or 170)
        targets = tdee(
            profile.sex,
            profile_weight,
            profile_height,
            profile.birth_date,
            profile.activity_level,
            goal_value,
        )

        target_calories_override = params.get("target_calories")
        target_calories: int
        if target_calories_override is not None:
            try:
                target_calories = int(target_calories_override)
            except (TypeError, ValueError):
                raise MenuPlanValidationError("target_calories must be an integer")
            if target_calories <= 0:
                raise MenuPlanValidationError("target_calories must be positive")
            targets = self._scale_targets(targets, target_calories)
        else:
            target_calories = int(targets.calories)

        budget_raw = params.get("budget")
        budget: Optional[Decimal]
        if budget_raw is not None:
            try:
                budget = Decimal(str(budget_raw))
            except Exception as exc:  # pragma: no cover - defensive
                raise MenuPlanValidationError("budget must be numeric") from exc
        else:
            budget = profile.daily_budget if profile.daily_budget else None

        variety_raw = raw_overrides.get("variety", 0.7)
        try:
            variety = float(variety_raw)
        except (TypeError, ValueError):
            raise MenuPlanValidationError("variety must be a number")
        variety = max(0.0, min(1.0, variety))

        meal_times_raw = raw_overrides.get("meal_times")
        meal_times = self._normalize_meal_times(meal_times_raw)
        if not meal_times:
            raise MenuPlanValidationError("meal_times cannot be empty")

        allergies_override = raw_overrides.get("allergies") or []
        allergies = _merge_unique(self._ensure_list(profile.allergies), self._ensure_list(allergies_override))

        city_override = raw_overrides.get("city")
        city_value = str(city_override).strip() if city_override else profile.city or None

        constraints_raw = raw_overrides.get("constraints") or {}
        if not isinstance(constraints_raw, Mapping):
            raise MenuPlanValidationError("constraints must be a mapping")
        constraints = json.loads(json.dumps(constraints_raw)) if constraints_raw else {}

        normalized_request = {
            "period_days": period_days,
            "target_calories": target_calories,
            "budget": str(budget) if budget is not None else None,
            "overrides": {
                "allergies": allergies,
                "goals": goal_override,
                "city": city_value,
                "variety": variety,
                "meal_times": meal_times,
                "constraints": constraints,
            },
        }
        raw_overrides_clean = {key: value for key, value in normalized_request["overrides"].items() if value not in (None, [], {})}
        normalized_request["overrides"] = raw_overrides_clean

        exclusions = self._ensure_list(profile.exclusions)

        return NormalizedParams(
            period_days=period_days,
            target_calories=target_calories,
            targets=targets,
            budget=budget,
            variety=variety,
            meal_times=meal_times,
            allergies=allergies,
            exclusions=exclusions,
            city=city_value,
            constraints=constraints,
            goal=goal_value,
            overrides=raw_overrides_clean,
            raw_request=normalized_request,
        )

    def _build_plan_payload(
        self,
        user: User,
        params: NormalizedParams,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        base_items = self._filter_service.filter(
            city=params.city,
            allergies=params.allergies,
            exclusions=params.exclusions,
            budget=params.budget,
        )
        if not base_items:
            logger.error("engine_error_no_items", extra={"user_id": user.id})
            raise MenuPlanEngineError("no available menu items for the provided filters")

        usage: Dict[int, int] = {}
        plan_entries: List[Dict[str, Any]] = []
        fallback_used_any = False

        max_repeat_per_item = self._max_repeat_per_item(params)
        restrictions = {"allergies": params.allergies, "exclusions": params.exclusions}

        for day_index in range(params.period_days):
            selection_service, tracker = self._instantiate_selection()
            day_items = self._apply_variety(base_items, usage, max_repeat_per_item)
            day_plan = selection_service.select_plan(
                items=day_items,
                targets=params.targets,
                restrictions=restrictions,
            )
            if not day_plan:
                logger.error("engine_error_empty_plan", extra={"user_id": user.id, "day": day_index + 1})
                raise MenuPlanEngineError("menu engine returned an empty plan")

            fallback_used_any = fallback_used_any or tracker.used
            normalized_entries = self._normalize_day_plan(day_plan, params.meal_times, day_index)
            if not normalized_entries:
                raise MenuPlanEngineError("generated plan is invalid")

            plan_entries.extend(normalized_entries)
            for entry in normalized_entries:
                item_id = entry["item_id"]
                usage[item_id] = usage.get(item_id, 0) + 1

        payload = {
            "targets": self._selection_proto.serialize_targets(params.targets),
            "plan": plan_entries,
        }

        price_map = {item.id: Decimal(item.price or 0) for item in base_items}
        summary = self._build_summary(params, plan_entries, price_map, fallback_used_any)
        metadata = {
            "request": params.raw_request,
            "generated_at": timezone.now().isoformat(),
            "fallback_used": fallback_used_any,
            "variety": params.variety,
            "constraints": params.constraints,
        }
        return payload, summary, metadata

    def _build_summary(
        self,
        params: NormalizedParams,
        plan_entries: Sequence[Mapping[str, Any]],
        price_map: Mapping[int, Decimal],
        fallback_used: bool,
    ) -> Dict[str, Any]:
        total_meals = len(plan_entries)
        unique_items = {entry.get("item_id") for entry in plan_entries if entry.get("item_id")}
        total_cost = Decimal("0.00")
        for entry in plan_entries:
            item_id = entry.get("item_id")
            qty = _as_float(entry.get("qty"), default=1.0)
            if not item_id or item_id not in price_map:
                continue
            total_cost += price_map[item_id] * Decimal(qty)
        daily_cost = total_cost / Decimal(max(1, params.period_days))

        summary = {
            "period_days": params.period_days,
            "daily_kcal": int(params.target_calories),
            "protein_g": int(params.targets.protein_g),
            "fat_g": int(params.targets.fat_g),
            "carbs_g": int(params.targets.carbs_g),
            "meals_total": total_meals,
            "unique_dishes": len(unique_items),
            "estimated_cost_rub_per_day": _decimal_two_places(daily_cost),
            "notes": f"engine=hybrid; fallback={'true' if fallback_used else 'false'}; variety={params.variety:.2f}",
        }
        return summary

    def _instantiate_selection(self) -> Tuple[MenuSelectionService, _FallbackRecorder]:
        tracker = _FallbackRecorder(self._selection_proto.fallback_strategy)
        selection = MenuSelectionService(
            provider_factory=self._selection_proto.provider_factory,
            fallback_strategy=tracker,
            context_items_limit=self._selection_proto.context_items_limit,
        )
        return selection, tracker

    def _normalize_day_plan(
        self,
        day_plan: Sequence[Mapping[str, Any]],
        meal_times: Sequence[str],
        day_index: int,
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for offset, entry in enumerate(day_plan):
            item_id = entry.get("item_id")
            if not item_id:
                continue
            try:
                item_id_int = int(item_id)
            except (TypeError, ValueError):
                continue
            qty = _as_float(entry.get("qty"), default=1.0)
            if qty <= 0:
                continue
            time_hint_raw = entry.get("time_hint") or meal_times[offset % len(meal_times)]
            if not isinstance(time_hint_raw, str):
                time_hint_raw = str(time_hint_raw)
            time_hint = time_hint_raw.strip() or meal_times[offset % len(meal_times)]
            scoped_time_hint = f"d{day_index + 1}_{time_hint}"[:16]
            normalized.append(
                {
                    "item_id": item_id_int,
                    "qty": qty,
                    "time_hint": scoped_time_hint,
                }
            )
        return normalized

    def _apply_variety(
        self,
        items: Sequence[MenuItem],
        usage: Mapping[int, int],
        max_repeat: int,
    ) -> List[MenuItem]:
        filtered: List[MenuItem] = []
        for item in items:
            used = usage.get(item.id, 0)
            if used >= max_repeat:
                continue
            filtered.append(item)
        return filtered or list(items)

    def _max_repeat_per_item(self, params: NormalizedParams) -> int:
        base = max(1, int(round((1 - params.variety) * params.period_days)))
        meals_per_day = max(1, len(params.meal_times))
        return max(1, base * meals_per_day // max(1, len(params.meal_times)) + 1)

    def _scale_targets(self, targets: Targets, new_calories: int) -> Targets:
        ratio = new_calories / max(1, targets.calories)
        return Targets(
            calories=new_calories,
            protein_g=int(round(targets.protein_g * ratio)),
            fat_g=int(round(targets.fat_g * ratio)),
            carbs_g=int(round(targets.carbs_g * ratio)),
        )

    def _map_goal(self, override: Optional[str], default_goal: str) -> str:
        mapping = {
            "lose_weight": Profile.Goal.LOSE,
            "gain_muscle": Profile.Goal.GAIN,
            "keep_fit": Profile.Goal.MAINTAIN,
        }
        if override and override in mapping:
            return mapping[override]
        return default_goal

    def _normalize_meal_times(self, meal_times: Any) -> List[str]:
        if not meal_times:
            return ["breakfast", "lunch", "dinner"]
        if not isinstance(meal_times, Iterable) or isinstance(meal_times, (str, bytes)):
            raise MenuPlanValidationError("meal_times must be a list of strings")
        normalized: List[str] = []
        for entry in meal_times:
            if not entry:
                continue
            value = str(entry).strip().lower()
            if value:
                normalized.append(value[:16])
        return normalized

    def _ensure_list(self, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    def _fingerprint(
        self,
        user_id: int,
        params: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> str:
        payload = {
            "user": user_id,
            "params": params,
            "context": context or {},
        }
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _get_user_plan(self, user: User, plan_id: int) -> MenuPlan:
        try:
            plan = MenuPlan.objects.select_related("snapshot").get(id=plan_id, user=user)
        except MenuPlan.DoesNotExist as exc:  # pragma: no cover - defensive
            raise MenuPlanPermissionError("plan not found") from exc
        return plan