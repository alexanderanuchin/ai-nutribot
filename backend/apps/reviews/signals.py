from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import update_rating


@receiver(post_save, sender=Review)
def review_post_save(sender: type[Review], instance: Review, created: bool, **_: Any) -> None:
    target = instance.target
    if target is None:
        return
    update_rating(target)


@receiver(post_delete, sender=Review)
def review_post_delete(sender: type[Review], instance: Review, **_: Any) -> None:
    target_model = instance.content_type.model_class()
    if not target_model:
        return
    try:
        target = target_model.objects.get(pk=instance.object_id)
    except target_model.DoesNotExist:  # type: ignore[attr-defined]
        return
    update_rating(target)
