from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .events import FeedEvent, get_event_broker
from .models import DealOffer, NewsArticle, Recipe
from .serializers import DealOfferEventSerializer, NewsArticleEventSerializer, RecipeEventSerializer


def _publish_event(event: FeedEvent) -> None:
    broker = get_event_broker()
    broker.publish(event)
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        event.group_name,
        {
            "type": "feed.event",
            "event": event.payload,
            "group": event.group_name,
        },
    )


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
    _publish_event(event)