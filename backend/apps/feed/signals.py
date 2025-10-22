from __future__ import annotations

from collections.abc import Iterable

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .events import FeedEvent, publish_feed_event, publish_news_article_event
from .models import DealOffer, NewsArticle, Recipe
from .serializers import DealOfferEventSerializer, RecipeEventSerializer


SIGNIFICANT_RECIPE_FIELDS: tuple[str, ...] = (
    "status",
    "title",
    "short_description",
    "description",
    "hero_image",
    "gallery",
    "cook_time_minutes",
    "difficulty",
    "calories",
    "protein",
    "fat",
    "carbs",
    "allergens",
    "diet_tags",
    "base_content",
    "is_premium",
    "price",
    "currency",
    "rating",
    "rating_count",
    "purchases_count",
)

SIGNIFICANT_DEAL_FIELDS: tuple[str, ...] = (
    "title",
    "product_name",
    "network",
    "city",
    "address",
    "is_online",
    "price_before",
    "price_after",
    "discount_percent",
    "valid_until",
    "offer_url",
    "image_url",
)


def _snapshot(instance, fields: Iterable[str]) -> dict[str, object]:
    return {field: getattr(instance, field) for field in fields}


def _event_for_instance(instance: Recipe | DealOffer) -> FeedEvent | None:
    if isinstance(instance, Recipe):
        if instance.status != Recipe.Status.PUBLISHED:
            return None
        serializer = RecipeEventSerializer(instance)
        group = "feed.recipes"
    elif isinstance(instance, DealOffer):
        serializer = DealOfferEventSerializer(instance)
        group = "feed.deals"
    else:  # pragma: no cover - defensive
        return None
    return FeedEvent(group_name=group, payload=serializer.data)


@receiver(post_save, sender=Recipe)
@receiver(post_save, sender=DealOffer)
def feed_model_saved(sender, instance, created, **kwargs):
    previous_state = getattr(instance, "_previous_state", None)
    if hasattr(instance, "_previous_state"):
        delattr(instance, "_previous_state")
    if created:
        event = _event_for_instance(instance)
        if event is None:
            return
        publish_feed_event(event)
        return

    if isinstance(instance, Recipe):
        fields = SIGNIFICANT_RECIPE_FIELDS
    else:
        fields = SIGNIFICANT_DEAL_FIELDS

    if not previous_state:
        return

    current_state = _snapshot(instance, fields)
    has_changes = any(current_state[field] != previous_state.get(field) for field in fields)
    if isinstance(instance, Recipe):
        previously_published = previous_state.get("status") == Recipe.Status.PUBLISHED
        currently_published = instance.status == Recipe.Status.PUBLISHED
        if previously_published != currently_published:
            has_changes = True
    if not has_changes:
        return
    event = _event_for_instance(instance)
    if event is None:
        return
    publish_feed_event(event)


@receiver(pre_save, sender=Recipe)
def cache_previous_recipe_state(sender, instance: Recipe, **kwargs):
    if instance.pk is None:
        instance._previous_state = None  # type: ignore[attr-defined]
        return
    try:
        previous = sender.objects.only(*SIGNIFICANT_RECIPE_FIELDS).get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None  # type: ignore[attr-defined]
        return
    instance._previous_state = _snapshot(previous, SIGNIFICANT_RECIPE_FIELDS)  # type: ignore[attr-defined]


@receiver(pre_save, sender=DealOffer)
def cache_previous_deal_state(sender, instance: DealOffer, **kwargs):
    if instance.pk is None:
        instance._previous_state = None  # type: ignore[attr-defined]
        return
    try:
        previous = sender.objects.only(*SIGNIFICANT_DEAL_FIELDS).get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None  # type: ignore[attr-defined]
        return
    instance._previous_state = _snapshot(previous, SIGNIFICANT_DEAL_FIELDS)  # type: ignore[attr-defined]


@receiver(pre_save, sender=NewsArticle)
def cache_previous_flag_state(sender, instance: NewsArticle, **kwargs):
    if instance.pk is None:
        instance._previous_is_flagged = instance.is_flagged  # type: ignore[attr-defined]
        return
    try:
        previous = sender.objects.only("is_flagged").get(pk=instance.pk)
    except sender.DoesNotExist:  # pragma: no cover - defensive
        instance._previous_is_flagged = instance.is_flagged  # type: ignore[attr-defined]
        return
    instance._previous_is_flagged = previous.is_flagged  # type: ignore[attr-defined]


@receiver(post_save, sender=NewsArticle)
def news_article_moderation_event(sender, instance: NewsArticle, created, **kwargs):
    if created:
        return
    previous_flagged = getattr(instance, "_previous_is_flagged", instance.is_flagged)
    if previous_flagged == instance.is_flagged:
        return
    publish_news_article_event(instance, action="moderated")
