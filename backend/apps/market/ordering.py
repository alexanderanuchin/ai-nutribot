from __future__ import annotations

import logging
from typing import Sequence

from django.conf import settings
from django.db.models import Expression, F, FloatField, IntegerField, Value
from django.db.models.functions import Cast, Coalesce
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

from nutribot.middleware import get_request_id


logger = logging.getLogger(__name__)

def json_float(path: str) -> Expression:
    """Cast a JSON path value to `float` for deterministic ordering."""

    return Cast(F(path), FloatField())


def json_int(path: str) -> Expression:
    """Cast a JSON path value to `int` for deterministic ordering."""

    return Cast(F(path), IntegerField())


def coalesce_json_float(paths: Sequence[str], default: float | None = None) -> Expression:
    """Return the first non-null float cast among the provided JSON paths."""

    expressions = [json_float(path) for path in paths]
    if not expressions:
        msg = "At least one JSON path is required to build a coalesced ordering expression"
        raise ValueError(msg)

    if default is not None:
        expressions.append(Value(default, FloatField()))

    if len(expressions) == 1:
        return expressions[0]

    return Coalesce(*expressions)


class MarketOrderingFilter(OrderingFilter):
    """Ordering filter that supports alias-to-expression mapping for market viewsets."""

    alias_attribute = "ordering_aliases"

    def _get_alias_map(self, view) -> dict[str, Expression]:
        alias_map = getattr(view, self.alias_attribute, None)
        if not alias_map:
            return {}
        return dict(alias_map)

    def get_ordering(self, request, queryset, view):  # type: ignore[override]
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",") if param.strip()]
            valid_fields = {
                item[0]
                for item in self.get_valid_fields(queryset, view, {"request": request})
            }
            invalid = sorted({term.lstrip("-") for term in fields if term.lstrip("-") not in valid_fields})
            if invalid:
                raise ValidationError(
                    {"ordering": [f"Unsupported ordering field(s): {', '.join(invalid)}"]}
                )
            if fields:
                return fields
        return self.get_default_ordering(view)

    def filter_queryset(self, request, queryset, view):  # type: ignore[override]
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        alias_map = self._get_alias_map(view)
        ordering_terms = list(ordering)
        annotations: dict[str, Expression] = {}
        for term in ordering_terms:
            field = term.lstrip("-")
            if field in alias_map:
                annotations[field] = alias_map[field]

        if annotations:
            queryset = queryset.annotate(**annotations)

        if settings.DEBUG:
            rid = getattr(request, "request_id", get_request_id())
            logger.info(
                "market ordering applied",
                extra={
                    "rid": rid,
                    "requested_ordering": ordering_terms,
                    "resolved_ordering": ordering_terms,
                    "alias_annotations": {alias: str(expr) for alias, expr in annotations.items()},
                },
            )

        return queryset.order_by(*ordering_terms)


__all__ = [
    "MarketOrderingFilter",
    "coalesce_json_float",
    "json_float",
    "json_int",
]
