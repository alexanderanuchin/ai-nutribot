from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Mapping, Sequence

from apps.catalog.models import MenuItem
from .llm_provider import LLMProvider, get_provider
from .services import Targets

logger = logging.getLogger(__name__)

Plan = List[Dict[str, Any]]
FallbackStrategy = Callable[[Sequence[MenuItem], Targets], Plan]
ProviderFactory = Callable[[], LLMProvider]


def greedy_knapsack(items: Sequence[MenuItem], targets: Targets) -> Plan:
    """Simple heuristic fallback when an LLM answer is unavailable."""
    picked: Plan = []
    remain = int(targets.calories)

    sortable_items: List[MenuItem] = [
        item for item in items if getattr(item, "nutrients", None) is not None
    ]
    sortable_items.sort(
        key=lambda item: abs(float(getattr(item.nutrients, "calories", 0)) - remain / 3 if remain else 0)
    )

    for item in sortable_items:
        if remain <= 0:
            break

        nutrients = item.nutrients
        calories = float(getattr(nutrients, "calories", 0) or 0)
        if calories <= 0:
            continue

        qty = max(1.0, round(remain / max(1.0, calories)))
        qty = min(qty, 3.0)

        picked.append(
            {
                "item_id": item.id,
                "title": item.title,
                "qty": qty,
                "time_hint": "any",
            }
        )
        remain -= int(calories * qty)

    return picked


class MenuSelectionService:
    """Compose a day plan using an LLM with a deterministic fallback."""

    def __init__(
        self,
        *,
        provider_factory: ProviderFactory | None = None,
        fallback_strategy: FallbackStrategy | None = None,
        context_items_limit: int = 120,
    ) -> None:
        self.provider_factory: ProviderFactory = provider_factory or get_provider
        self.fallback_strategy: FallbackStrategy = fallback_strategy or greedy_knapsack
        self.context_items_limit = max(1, int(context_items_limit))

    def serialize_targets(self, targets: Targets) -> Dict[str, int]:
        protein = int(targets.protein_g)
        fat = int(targets.fat_g)
        carbs = int(targets.carbs_g)
        return {
            "calories": int(targets.calories),
            "protein": protein,
            "protein_g": protein,
            "fat": fat,
            "fat_g": fat,
            "carbs": carbs,
            "carbs_g": carbs,
        }

    def _normalize_items(self, items: Sequence[MenuItem]) -> List[MenuItem]:
        normalized: List[MenuItem] = []
        for item in items:
            if getattr(item, "nutrients", None) is None:
                continue
            normalized.append(item)
        return normalized

    def _normalize_restrictions(self, restrictions: Mapping[str, Any] | None) -> Dict[str, Any]:
        if not restrictions:
            return {"allergies": [], "exclusions": []}

        normalized: Dict[str, Any] = {}
        for key, value in restrictions.items():
            if isinstance(value, (list, tuple, set)):
                normalized[key] = [entry for entry in value if entry]
            else:
                normalized[key] = value
        normalized.setdefault("allergies", [])
        normalized.setdefault("exclusions", [])
        return normalized

    def _serialize_items(self, items: Sequence[MenuItem]) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for item in items[: self.context_items_limit]:
            nutrients = item.nutrients
            tags = item.tags or []
            if not isinstance(tags, list):
                if isinstance(tags, (tuple, set)):
                    tags = list(tags)
                elif tags:
                    tags = [tags]
                else:
                    tags = []

            payload.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "kcal": float(getattr(nutrients, "calories", 0) or 0),
                    "protein": float(getattr(nutrients, "protein", 0) or 0),
                    "fat": float(getattr(nutrients, "fat", 0) or 0),
                    "carbs": float(getattr(nutrients, "carbs", 0) or 0),
                    "tags": tags,
                    "price": item.price,
                }
            )
        return payload

    def select_plan(
        self,
        *,
        items: Sequence[MenuItem],
        targets: Targets,
        restrictions: Mapping[str, Any] | None = None,
    ) -> Plan:
        normalized_items = self._normalize_items(items)
        restrictions_payload = self._normalize_restrictions(restrictions)
        context = {
            "targets": self.serialize_targets(targets),
            "items": self._serialize_items(normalized_items),
            "restrictions": restrictions_payload,
        }

        plan: Plan
        try:
            plan = self.provider_factory().compose_menu(context)
        except Exception:  # pragma: no cover - defensive
            logger.exception("LLM provider failed to compose menu")
            plan = []

        if not plan:
            plan = self.fallback_strategy(normalized_items, targets)

        return plan