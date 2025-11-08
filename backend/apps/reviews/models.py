from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Type

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

if TYPE_CHECKING:  # pragma: no cover
    from django.contrib.auth import get_user_model

    User = get_user_model()


class ReviewQuerySet(models.QuerySet["Review"]):
    def for_instance(self, instance: models.Model) -> "ReviewQuerySet":
        content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
        return self.filter(content_type=content_type, object_id=instance.pk)

    def for_model(self, model: Type[models.Model]) -> "ReviewQuerySet":
        content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
        return self.filter(content_type=content_type)


class Review(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Оценка по пятизвёздочной шкале",
    )
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"], name="reviews_target_idx"),
            models.Index(fields=["author", "content_type"], name="reviews_author_target_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "content_type", "object_id"],
                name="reviews_unique_author_target",
            ),
        ]
        ordering = ("-created_at", "-id")
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        return f"Review<{self.content_type_id}:{self.object_id}:{self.author_id}>"

    @classmethod
    def eligible_content_types(cls) -> Iterable[ContentType]:
        from apps.market.models import MealPlan, Product, Recipe, Store

        allowed_models: tuple[Type[models.Model], ...] = (Store, Product, Recipe, MealPlan)
        return (
            ContentType.objects.get_for_model(model, for_concrete_model=False)
            for model in allowed_models
        )

    @classmethod
    def is_supported_model(cls, model: Type[models.Model]) -> bool:
        from apps.market.models import MealPlan, Product, Recipe, Store

        return model in {Store, Product, Recipe, MealPlan}
