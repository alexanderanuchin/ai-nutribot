from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .events import FeedEvent, publish_feed_event
from .models import DealOffer, NewsArticle, Recipe
from .serializers import DealOfferEventSerializer, NewsArticleEventSerializer, RecipeEventSerializer


def _event_for_instance(instance: NewsArticle | Recipe | DealOffer) -> FeedEvent | None:
    if isinstance(instance, NewsArticle):
        serializer = NewsArticleEventSerializer(instance)
        group = "feed.news"
    elif isinstance(instance, Recipe):
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


@receiver(post_save, sender=NewsArticle)
@receiver(post_save, sender=Recipe)
@receiver(post_save, sender=DealOffer)
def feed_model_saved(sender, instance, created, **kwargs):
    if not created:
        return
    event = _event_for_instance(instance)
    if event is None:
        return
    publish_feed_event(event)