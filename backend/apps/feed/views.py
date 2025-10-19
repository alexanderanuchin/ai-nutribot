from __future__ import annotations

import logging
from typing import List

from django.db import models
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from nutribot.middleware import get_request_id

from .authentication import authenticate_access_token, authenticate_integration_key, extract_token_from_request
from .events import format_sse, get_event_broker
from .filters import filter_deals, filter_news, filter_recipes
from .models import DealOffer, FeedTag, NewsArticle, Recipe, RecipePurchase, RecipeReaction
from .pagination import FeedCursorPagination
from .serializers import (
    DealOfferSerializer,
    NewsArticleSerializer,
    RecipePurchaseSerializer,
    RecipeSerializer,
    RecipeWriteSerializer,
)
from .services import create_purchase, publish_recipe

logger = logging.getLogger("feed.api")


class FeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FeedCursorPagination

    def get(self, request, *args, **kwargs):
        feed_type = request.query_params.get("type", "news")
        paginator = self.pagination_class()
        paginator.ordering = "-published_at" if feed_type == "news" else "-created_at"

        if feed_type == "news":
            queryset = NewsArticle.objects.filter(is_flagged=False).prefetch_related("tags")
            queryset = filter_news(queryset, request.query_params)
            serializer_class = NewsArticleSerializer
        elif feed_type == "recipes":
            queryset = (
                Recipe.objects.filter(status=Recipe.Status.PUBLISHED)
                .prefetch_related("tags", "steps")
                .select_related("author")
            )
            queryset = filter_recipes(queryset, request.query_params)
            serializer_class = RecipeSerializer
        elif feed_type == "deals":
            queryset = DealOffer.objects.prefetch_related("tags")
            queryset = filter_deals(queryset, request.query_params)
            serializer_class = DealOfferSerializer
        else:
            raise ValidationError({"type": "Unsupported feed type"})

        page = paginator.paginate_queryset(queryset, request)
        if feed_type == "recipes":
            self._attach_recipe_metadata(page, request)
        serializer = serializer_class(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def _attach_recipe_metadata(self, recipes: List[Recipe], request):
        if not recipes:
            return
        recipe_ids = [recipe.id for recipe in recipes]
        reaction_map: dict[int, dict[str, int]] = {}
        reactions = (
            RecipeReaction.objects.filter(recipe_id__in=recipe_ids)
            .values("recipe_id", "kind")
            .annotate(total=models.Count("id"))
        )
        for row in reactions:
            reaction_map.setdefault(row["recipe_id"], {})[row["kind"]] = row["total"]

        purchases = []
        if request.user.is_authenticated:
            purchases = list(
                RecipePurchase.objects.filter(
                    recipe_id__in=recipe_ids,
                    user=request.user,
                    status=RecipePurchase.Status.COMPLETED,
                )
            )
        for recipe in recipes:
            recipe.reaction_counts = reaction_map.get(recipe.id, {})
            recipe.prefetched_purchases = [p for p in purchases if p.recipe_id == recipe.id]


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RecipeSerializer
    pagination_class = FeedCursorPagination
    http_method_names = ["get", "post", "put", "patch"]

    def get_queryset(self):
        user = self.request.user
        if self.action in {"list"}:
            queryset = Recipe.objects.filter(status=Recipe.Status.PUBLISHED)
        elif self.action in {"retrieve", "premium"}:
            queryset = Recipe.objects.filter(Q(status=Recipe.Status.PUBLISHED) | Q(author=user))
        elif self.action in {"purchase"}:
            queryset = Recipe.objects.filter(status=Recipe.Status.PUBLISHED)
        else:
            queryset = Recipe.objects.filter(author=user)
        return queryset.prefetch_related("tags", "steps").distinct()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return RecipeWriteSerializer
        return RecipeSerializer

    def perform_update(self, serializer):
        recipe = self.get_object()
        if recipe.author_id != self.request.user.id:
            raise PermissionDenied("Можно редактировать только свои рецепты")
        serializer.save()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        recipe = self.get_object()
        if recipe.author_id != request.user.id and not request.user.is_staff:
            raise PermissionDenied("Недостаточно прав для публикации")
        publish_recipe(recipe, request=request)
        return Response({"status": "published"})

    @action(detail=True, methods=["post"], url_path="purchase")
    def purchase(self, request, pk=None):
        recipe = self.get_object()
        purchase = create_purchase(user=request.user, recipe=recipe, request=request)
        serializer = RecipePurchaseSerializer(purchase, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="premium")
    def premium(self, request, pk=None):
        recipe = self.get_object()
        has_access = False
        if not recipe.is_premium:
            has_access = True
        elif recipe.author_id == request.user.id or request.user.is_staff:
            has_access = True
        else:
            has_access = RecipePurchase.objects.filter(
                recipe=recipe,
                user=request.user,
                status=RecipePurchase.Status.COMPLETED,
            ).exists()
        if not has_access:
            raise PermissionDenied("Требуется покупка рецепта")
        return Response({
            "id": recipe.id,
            "premium_content": recipe.premium_content,
        })


class FeedEventStreamView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        token = extract_token_from_request(request)
        user = authenticate_access_token(token) if token else None
        if not user:
            raise PermissionDenied("Authentication required")
        request.user = user
        feed_type = request.query_params.get("type")
        allowed_groups = {
            "news": "feed.news",
            "recipes": "feed.recipes",
            "deals": "feed.deals",
        }
        group_filter = allowed_groups.get(feed_type)
        broker = get_event_broker()
        subscriber_id, queue = broker.subscribe()
        rid = getattr(request, "request_id", get_request_id())

        def event_stream():
            try:
                yield b":ok\n\n"
                for event in broker.iter_events(queue):
                    if group_filter and event.group_name != group_filter:
                        continue
                    for chunk in format_sse(event):
                        yield chunk
            finally:
                broker.unsubscribe(subscriber_id)
                logger.debug("sse client disconnected", extra={"rid": rid, "subscriber_id": subscriber_id})

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class NewsIngestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        authenticate_integration_key(request)
        data = request.data
        required = ["source_id", "title", "lead", "source_name", "source_url"]
        for field in required:
            if field not in data:
                raise ValidationError({field: "Обязательное поле"})
        published_at_value = data.get("published_at")
        parsed_published = parse_datetime(published_at_value) if published_at_value else None
        article, created = NewsArticle.objects.update_or_create(
            source_id=data["source_id"],
            defaults={
                "title": data["title"],
                "lead": data["lead"],
                "source_name": data["source_name"],
                "source_url": data["source_url"],
                "published_at": parsed_published or timezone.now(),
                "preview_image_url": data.get("preview_image_url", ""),
                "is_flagged": data.get("is_flagged", False),
            },
        )
        tags = data.get("tags", [])
        if tags:
            tag_objects = FeedTag.objects.filter(slug__in=tags)
            article.tags.set(tag_objects)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({"id": article.id}, status=status_code)


class DealIngestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        authenticate_integration_key(request)
        data = request.data
        required = [
            "external_id",
            "title",
            "product_name",
            "network",
            "city",
            "price_before",
            "price_after",
            "discount_percent",
            "valid_until",
        ]
        for field in required:
            if field not in data:
                raise ValidationError({field: "Обязательное поле"})
        valid_until_value = data.get("valid_until")
        parsed_valid_until = parse_datetime(valid_until_value) if valid_until_value else None
        offer, created = DealOffer.objects.update_or_create(
            external_id=data["external_id"],
            defaults={
                "title": data["title"],
                "product_name": data["product_name"],
                "network": data["network"],
                "city": data["city"],
                "address": data.get("address", ""),
                "is_online": data.get("is_online", False),
                "price_before": data["price_before"],
                "price_after": data["price_after"],
                "discount_percent": data["discount_percent"],
                "valid_until": parsed_valid_until or timezone.now(),
                "offer_url": data.get("offer_url", ""),
                "image_url": data.get("image_url", ""),
            },
        )
        tags = data.get("tags", [])
        if tags:
            tag_objects = FeedTag.objects.filter(slug__in=tags)
            offer.tags.set(tag_objects)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({"id": offer.id}, status=status_code)