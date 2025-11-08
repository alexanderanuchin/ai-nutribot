from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from django.contrib.contenttypes.models import ContentType
from django.db import models

from .models import Review


@dataclass(slots=True)
class RatingSummary:
    average: float | None
    count: int

    @property
    def is_empty(self) -> bool:
        return self.count == 0


@runtime_checkable
class SupportsMetadata(Protocol):
    metadata: dict

    def save(self, update_fields: list[str] | tuple[str, ...] | None = None) -> None: ...


def compute_rating_for_instance(instance: models.Model) -> RatingSummary:
    queryset = Review.objects.for_instance(instance)
    aggregated = queryset.aggregate(
        average=models.Avg("rating", default=None),
        count=models.Count("id"),
    )
    average = aggregated.get("average")
    if average is None:
        return RatingSummary(average=None, count=int(aggregated.get("count") or 0))
    return RatingSummary(average=float(average), count=int(aggregated.get("count") or 0))


def apply_rating_to_instance(instance: SupportsMetadata, summary: RatingSummary) -> bool:
    metadata = getattr(instance, "metadata", {}) or {}
    changed = False
    if summary.is_empty:
        if "rating" in metadata or "rating_count" in metadata:
            metadata.pop("rating", None)
            metadata.pop("rating_count", None)
            changed = True
    else:
        rounded = round(summary.average or 0.0, 2)
        if metadata.get("rating") != rounded or metadata.get("rating_count") != summary.count:
            metadata["rating"] = rounded
            metadata["rating_count"] = summary.count
            changed = True
    if changed:
        instance.metadata = metadata
        update_fields = ["metadata"]
        if hasattr(instance, "updated_at"):
            update_fields.append("updated_at")
        instance.save(update_fields=update_fields)
    return changed


def update_rating(instance: models.Model) -> RatingSummary:
    summary = compute_rating_for_instance(instance)
    if isinstance(instance, SupportsMetadata):
        apply_rating_to_instance(instance, summary)
    return summary


def get_supported_content_type(model: type[models.Model]) -> ContentType:
    if not Review.is_supported_model(model):
        raise ValueError(f"Unsupported review target model: {model!r}")
    return ContentType.objects.get_for_model(model, for_concrete_model=False)
