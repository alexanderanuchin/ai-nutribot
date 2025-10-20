from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .events import FeedEvent, publish_feed_event, publish_news_article_event
from .models import DealOffer, NewsArticle, Recipe
from .serializers import DealOfferEventSerializer, RecipeEventSerializer


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
    if not created:
        return
    event = _event_for_instance(instance)
    if event is None:
        return
    publish_feed_event(event)


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
