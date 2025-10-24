from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, List

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
from .events import format_sse, get_event_broker, publish_news_article_event
from .filters import filter_deals, filter_news, filter_recipes
from .models import DealOffer, FeedTag, NewsArticle, Recipe, RecipePurchase, RecipeReaction
from .pagination import FeedCursorPagination
from .serializers import (
    DealOfferSerializer,
    NewsArticleIngestSerializer,
    NewsArticleSerializer,
    RecipePurchaseSerializer,
    RecipeSerializer,
    RecipeWriteSerializer,
)
from .services import create_purchase, publish_recipe
from .services.ingest_pipeline import normalize_and_translate_article

logger = logging.getLogger("feed.api")


class FeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FeedCursorPagination

    @staticmethod
    def _parse_flag_filter(value: str | None) -> bool | None:
        if value is None:
            return False
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "flagged", "moderated"}:
            return True
        if normalized in {"0", "false", "no", "clean"}:
            return False
        if normalized in {"any", "all", "*"}:
            return None
        return False

    def get(self, request, *args, **kwargs):
        feed_type = request.query_params.get("type", "news")
        paginator = self.pagination_class()
        paginator.ordering = (
            ("-published_at", "-id")
            if feed_type == "news"
            else ("-created_at", "-id")
        )

        if feed_type == "news":
            flag_filter = self._parse_flag_filter(request.query_params.get("is_flagged"))
            queryset = NewsArticle.objects.all().prefetch_related("tags")
            if flag_filter is True:
                queryset = queryset.filter(is_flagged=True)
            elif flag_filter is False:
                queryset = queryset.filter(is_flagged=False)
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
    serializer_class = NewsArticleIngestSerializer

    def post(self, request, *args, **kwargs):
        authenticate_integration_key(request)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        rid = getattr(request, "request_id", get_request_id())
        now = timezone.now()
        tags_payload = payload.pop("tags", [])
        published_at = payload.pop("published_at", None)
        ingested_at = payload.pop("ingested_at", None) or now
        ingestion_metadata = payload.pop("ingestion_metadata", None)
        ingestion_source = payload.pop("ingestion_source", "") or "api"
        normalized_article = normalize_and_translate_article(
            {
                "title": payload.get("title"),
                "lead": payload.get("lead"),
                "body": payload.get("body"),
            },
            rid=rid,
        )
        normalized_title = normalized_article.get("title") or payload.get("title")
        normalized_lead = normalized_article.get("lead") or payload.get("lead")
        normalized_body = normalized_article.get("body")

        create_defaults = {
            "title": normalized_title,
            "lead": normalized_lead,
            "body": normalized_body or None,
            "title_orig": normalized_article.get("title_orig"),
            "lead_orig": normalized_article.get("lead_orig"),
            "body_orig": normalized_article.get("body_orig"),
            "lang": normalized_article.get("lang", "und"),
            "translated": normalized_article.get("translated", False),
            "translation_provider": normalized_article.get("translation_provider", ""),
            "source_name": payload.get("source_name"),
            "source_url": payload.get("source_url"),
            "published_at": published_at or now,
            "preview_image_url": payload.get("preview_image_url", ""),
            "tonality": payload.get("tonality", NewsArticle.Tonality.NEUTRAL),
            "source_categories": payload.get("source_categories", []),
            "toxicity_score": payload.get("toxicity_score", Decimal("0")),
            "clickbait_score": payload.get("clickbait_score", Decimal("0")),
            "is_flagged": payload.get("is_flagged", False),
            "ingested_at": ingested_at,
            "ingestion_source": ingestion_source,
            "ingestion_rid": rid,
            "ingestion_metadata": ingestion_metadata or {},
        }

        article, created = NewsArticle.objects.get_or_create(
            source_id=payload["source_id"], defaults=create_defaults
        )

        update_fields = set()
        if not created:
            field_map = {
                "title": normalized_title,
                "lead": normalized_lead,
                "source_name": payload.get("source_name"),
                "source_url": payload.get("source_url"),
                "preview_image_url": payload.get("preview_image_url"),
                "tonality": payload.get("tonality"),
                "toxicity_score": payload.get("toxicity_score"),
                "clickbait_score": payload.get("clickbait_score"),
                "is_flagged": payload.get("is_flagged"),
            }
            if "body" in payload:
                field_map["body"] = normalized_body or None
            for field, value in field_map.items():
                if value is not None:
                    setattr(article, field, value)
                    update_fields.add(field)
            translation_map = {
                "title_orig": normalized_article.get("title_orig"),
                "lead_orig": normalized_article.get("lead_orig"),
                "body_orig": normalized_article.get("body_orig"),
                "lang": normalized_article.get("lang", article.lang or "und"),
                "translated": normalized_article.get("translated", False),
                "translation_provider": normalized_article.get("translation_provider", ""),
            }
            for field, value in translation_map.items():
                setattr(article, field, value)
                update_fields.add(field)
            if published_at:
                article.published_at = published_at
                update_fields.add("published_at")
            if "source_categories" in payload:
                article.source_categories = payload.get("source_categories", [])
                update_fields.add("source_categories")
            article.ingested_at = ingested_at
            article.ingestion_source = ingestion_source
            article.ingestion_rid = rid
            update_fields.update({"ingested_at", "ingestion_source", "ingestion_rid"})
            if ingestion_metadata is not None:
                existing_meta = article.ingestion_metadata or {}
                if isinstance(existing_meta, dict) and isinstance(ingestion_metadata, dict):
                    merged_meta = {**existing_meta, **ingestion_metadata}
                else:
                    merged_meta = ingestion_metadata
                article.ingestion_metadata = merged_meta
                update_fields.add("ingestion_metadata")
            article.save(update_fields=list(update_fields))

        if tags_payload:
            tag_instances = self._upsert_tags(tags_payload)
            article.tags.set(tag_instances)
        elif created:
            article.tags.clear()

        action = "created" if created else "updated"
        logger.info(
            "news article ingested",
            extra={
                "rid": rid,
                "source_id": article.source_id,
                "article_id": article.id,
                "action": action,
            },
        )
        publish_news_article_event(article, action=action, rid=rid)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({"id": article.id}, status=status_code)

    def _upsert_tags(self, tags_payload: list[dict[str, Any]]):
        tag_instances = []
        for tag in tags_payload:
            slug = tag["slug"].lower()
            defaults = {
                "name": tag.get("name") or tag.get("slug"),
                "kind": tag.get("kind") or FeedTag.Kind.NEWS,
            }
            obj, created = FeedTag.objects.get_or_create(slug=slug, defaults=defaults)
            if not created:
                updates = {}
                if tag.get("name") and obj.name != tag["name"]:
                    updates["name"] = tag["name"]
                if tag.get("kind") and obj.kind != tag["kind"]:
                    updates["kind"] = tag["kind"]
                if updates:
                    for field, value in updates.items():
                        setattr(obj, field, value)
                    obj.save(update_fields=list(updates.keys()))
            tag_instances.append(obj)
        return tag_instances


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
