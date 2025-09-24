from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Sequence

from django.db import connection
from django.db.models import Q, QuerySet

from apps.catalog.models import MenuItem, Restaurant, Store


class MenuConstraintFilter:
    """Base class for filters applied to the menu queryset."""

    def apply(self, queryset: QuerySet[MenuItem], criteria: Mapping[str, Any]) -> QuerySet[MenuItem]:
        return queryset


@dataclass(frozen=True)
class AvailabilityFilter(MenuConstraintFilter):
    """Keep only items that are marked as available."""

    field_name: str = "is_available"

    def apply(self, queryset: QuerySet[MenuItem], criteria: Mapping[str, Any]) -> QuerySet[MenuItem]:
        return queryset.filter(**{self.field_name: True})


@dataclass(frozen=True)
class OverlapExclusionFilter(MenuConstraintFilter):
    """Exclude items when their JSON field overlaps with banned values."""

    field_name: str
    criteria_key: str

    def apply(self, queryset: QuerySet[MenuItem], criteria: Mapping[str, Any]) -> QuerySet[MenuItem]:
        values = [value for value in criteria.get(self.criteria_key, []) if value]
        if not values:
            return queryset

        if connection.vendor == "sqlite":
            needle = {str(value) for value in values}
            ids_with_overlap: list[int] = []
            for item_id, stored in queryset.values_list("id", self.field_name):
                if not stored:
                    continue
                if isinstance(stored, (list, tuple, set)):
                    stored_values = {str(entry) for entry in stored}
                else:
                    stored_values = {str(stored)}
                if needle & stored_values:
                    ids_with_overlap.append(item_id)
            if not ids_with_overlap:
                return queryset
            return queryset.exclude(id__in=ids_with_overlap)

        return queryset.exclude(**{f"{self.field_name}__overlap": values})


@dataclass(frozen=True)
class BudgetFilter(MenuConstraintFilter):
    """Apply an upper price limit when provided."""

    criteria_key: str = "budget"
    field_name: str = "price"

    def apply(self, queryset: QuerySet[MenuItem], criteria: Mapping[str, Any]) -> QuerySet[MenuItem]:
        budget = criteria.get(self.criteria_key)
        if not budget:
            return queryset
        try:
            budget_value = int(budget)
        except (TypeError, ValueError):
            return queryset
        if budget_value <= 0:
            return queryset
        return queryset.filter(**{f"{self.field_name}__lte": budget_value})


@dataclass(frozen=True)
class CityFilter(MenuConstraintFilter):
    """Restrict menu items to the specified city when possible."""

    criteria_key: str = "city"

    def apply(self, queryset: QuerySet[MenuItem], criteria: Mapping[str, Any]) -> QuerySet[MenuItem]:
        city = criteria.get(self.criteria_key)
        if not city:
            return queryset

        restaurants = Restaurant.objects.filter(city=city, is_active=True).values_list("id", flat=True)
        stores = Store.objects.filter(city=city, is_active=True).values_list("id", flat=True)

        return queryset.filter(
            Q(source="restaurant", source_id__in=restaurants)
            | Q(source="store", source_id__in=stores)
        )


class MenuFilterService:
    """Apply a sequence of filters to produce a shortlist of menu items."""

    def __init__(
        self,
        *,
        queryset_factory: Callable[[], QuerySet[MenuItem]] | None = None,
        filters: Sequence[MenuConstraintFilter] | None = None,
        limit: int = 300,
    ) -> None:
        self.queryset_factory = queryset_factory or (lambda: MenuItem.objects.all())
        self.filters: Sequence[MenuConstraintFilter] = filters or (
            AvailabilityFilter(),
            CityFilter(),
            OverlapExclusionFilter(field_name="allergens", criteria_key="allergies"),
            OverlapExclusionFilter(field_name="exclusions", criteria_key="exclusions"),
            BudgetFilter(),
        )
        self.limit = max(1, int(limit))

    def _normalize_criteria(self, raw_criteria: Mapping[str, Any]) -> Dict[str, Any]:
        criteria: Dict[str, Any] = dict(raw_criteria)
        for key in ("allergies", "exclusions"):
            values = criteria.get(key)
            if not values:
                criteria[key] = []
            elif isinstance(values, (set, tuple)):
                criteria[key] = [value for value in values if value]
            elif isinstance(values, list):
                criteria[key] = [value for value in values if value]
            else:
                criteria[key] = [values]
        return criteria

    def filter(self, **criteria: Any) -> list[MenuItem]:
        normalized = self._normalize_criteria(criteria)
        queryset = self.queryset_factory()
        for filter_ in self.filters:
            queryset = filter_.apply(queryset, normalized)
        queryset = queryset.select_related("nutrients")
        return list(queryset[: self.limit])