"""Serializers for nutrition plan API endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from rest_framework import serializers


class ConstraintsField(serializers.DictField):
    """A dict field that normalizes Decimal values to strings."""

    def to_representation(self, value):  # pragma: no cover - thin wrapper
        data = super().to_representation(value)
        return _stringify_decimal(data)


def _stringify_decimal(data: Any) -> Any:
    if isinstance(data, Decimal):
        return f"{data:.2f}"
    if isinstance(data, dict):
        return {key: _stringify_decimal(val) for key, val in data.items()}
    if isinstance(data, list):
        return [_stringify_decimal(val) for val in data]
    return data


class MenuPlanOverridesSerializer(serializers.Serializer):
    allergies = serializers.ListField(child=serializers.CharField(), required=False)
    goals = serializers.ChoiceField(
        choices=("lose_weight", "gain_muscle", "keep_fit"), required=False
    )
    city = serializers.CharField(required=False, allow_blank=True)
    variety = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    meal_times = serializers.ListField(child=serializers.CharField(), required=False)
    constraints = ConstraintsField(required=False)


class MenuPlanGenerateSerializer(serializers.Serializer):
    period_days = serializers.IntegerField(min_value=1, max_value=30)
    target_calories = serializers.IntegerField(required=False, min_value=1)
    budget = serializers.DecimalField(required=False, max_digits=8, decimal_places=2)
    overrides = MenuPlanOverridesSerializer(required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        overrides = attrs.get("overrides") or {}
        if overrides:
            overrides = dict(overrides)
            if "constraints" in overrides and overrides["constraints"] is None:
                overrides.pop("constraints")
            attrs["overrides"] = overrides
        return attrs


class MenuPlanRegenerateSerializer(serializers.Serializer):
    overrides = MenuPlanOverridesSerializer(required=False)
    target_calories = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        overrides = dict(attrs.get("overrides") or {})
        if "target_calories" in attrs:
            overrides["target_calories"] = attrs.pop("target_calories")
        if overrides:
            attrs["overrides"] = overrides
        return attrs