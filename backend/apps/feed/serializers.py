from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable

from django.db.models import Count
from django.utils import formats, timezone, translation
from rest_framework import serializers

from .models import DealOffer, FeedTag, NewsArticle, Recipe, RecipePurchase, RecipeReaction, RecipeStep
from .utils.datetime import to_moscow


class FeedTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedTag
        fields = ["id", "name", "slug", "kind"]


class FeedTagIngestField(serializers.Field):
    """Accepts flexible tag payloads (slug strings, dicts with children)."""

    default_error_messages = {
        "invalid": "Неверный формат тегов",
        "missing_slug": "Для каждого тега требуется slug",
    }

    def to_internal_value(self, data: Any) -> list[dict[str, Any]]:
        def _flatten(items: Iterable[Any]) -> Iterable[dict[str, Any]]:
            for item in items:
                if isinstance(item, str):
                    yield {"slug": item}
                    continue
                if not isinstance(item, dict):
                    self.fail("invalid")
                slug = item.get("slug") or item.get("name")
                if not slug:
                    self.fail("missing_slug")
                payload = {
                    "slug": slug,
                    "name": item.get("name"),
                    "kind": item.get("kind"),
                }
                yield payload
                nested = item.get("children") or item.get("tags")
                if nested:
                    yield from _flatten(nested)

        if data in (None, ""):
            return []
        if not isinstance(data, list):
            self.fail("invalid")
        flattened = list(_flatten(data))
        unique: dict[str, dict[str, Any]] = {}
        for entry in flattened:
            slug = entry["slug"].lower()
            if slug not in unique:
                unique[slug] = entry
            else:
                # merge optional fields while keeping first truthy values
                for key in ("name", "kind"):
                    if not unique[slug].get(key) and entry.get(key):
                        unique[slug][key] = entry[key]
        return list(unique.values())

    def to_representation(self, value: Any) -> Any:  # pragma: no cover - not used
        return value


class NewsArticleSerializer(serializers.ModelSerializer):
    tags = FeedTagSerializer(many=True, read_only=True)
    published_at = serializers.SerializerMethodField()
    published_at_localized = serializers.SerializerMethodField()
    published_at_msk = serializers.SerializerMethodField()
    timezone_label = serializers.SerializerMethodField()

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "source_id",
            "title",
            "lead",
            "body",
            "title_orig",
            "lead_orig",
            "body_orig",
            "lang",
            "translated",
            "translation_provider",
            "source_name",
            "source_url",
            "published_at",
            "published_at_localized",
            "published_at_msk",
            "timezone_label",
            "preview_image_url",
            "tonality",
            "source_categories",
            "toxicity_score",
            "clickbait_score",
            "is_flagged",
            "is_published",
            "ingested_at",
            "ingestion_source",
            "ingestion_rid",
            "ingestion_metadata",
            "created_at",
            "updated_at",
            "tags",
        ]
        read_only_fields = tuple(fields)

    def get_published_at(self, obj: NewsArticle) -> str | None:
        dt = to_moscow(obj.published_at)
        return dt.isoformat() if dt else None

    def get_published_at_localized(self, obj: NewsArticle) -> str | None:
        if not obj.published_at:
            return None
        value = obj.published_at
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        value = timezone.localtime(value)
        language = None
        request = self.context.get("request")
        if request is not None:
            language = getattr(request, "LANGUAGE_CODE", None)
        if language:
            with translation.override(language):
                return formats.date_format(value, format="DATETIME_FORMAT")
        return formats.date_format(value, format="DATETIME_FORMAT")

    def get_published_at_msk(self, obj: NewsArticle) -> str | None:
        return _format_msk_iso(obj.published_at)

    def get_timezone_label(self, obj: NewsArticle) -> str:
        return "MSK"


class NewsArticleIngestSerializer(serializers.Serializer):
    source_id = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=240)
    lead = serializers.CharField()
    body = serializers.CharField(required=False, allow_blank=True)
    source_name = serializers.CharField(max_length=120)
    source_url = serializers.URLField()
    published_at = serializers.DateTimeField(required=False)
    preview_image_url = serializers.URLField(required=False, allow_blank=True)
    tonality = serializers.ChoiceField(choices=NewsArticle.Tonality.choices, required=False)
    source_categories = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, allow_empty=True
    )
    toxicity_score = serializers.DecimalField(
        max_digits=5, decimal_places=4, required=False, min_value=Decimal("0")
    )
    clickbait_score = serializers.DecimalField(
        max_digits=5, decimal_places=4, required=False, min_value=Decimal("0")
    )
    is_flagged = serializers.BooleanField(required=False)
    ingested_at = serializers.DateTimeField(required=False)
    ingestion_source = serializers.CharField(max_length=64, required=False, allow_blank=True)
    ingestion_metadata = serializers.JSONField(required=False)
    tags = FeedTagIngestField(required=False)


class RecipeStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeStep
        fields = ["id", "order", "text", "media_url"]
        read_only_fields = ["id"]


class RecipeSerializer(serializers.ModelSerializer):
    tags = FeedTagSerializer(many=True, read_only=True)
    steps = RecipeStepSerializer(many=True, read_only=True)
    reaction_summary = serializers.SerializerMethodField()
    is_purchased = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "slug",
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
            "tags",
            "steps",
            "reaction_summary",
            "is_purchased",
        ]
        read_only_fields = [
            "status",
            "rating",
            "rating_count",
            "purchases_count",
        ]

    def get_reaction_summary(self, obj: Recipe) -> Dict[str, int]:
        reaction_map = getattr(obj, "reaction_counts", None)
        if reaction_map is not None:
            return reaction_map
        counts = (
            RecipeReaction.objects.filter(recipe=obj)
            .values("kind")
            .annotate(total=Count("id"))
        )
        return {item["kind"]: item["total"] for item in counts}

    def get_is_purchased(self, obj: Recipe) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        purchases = getattr(obj, "prefetched_purchases", None)
        if purchases is not None:
            return any(purchase.user_id == user.id for purchase in purchases)
        return RecipePurchase.objects.filter(user=user, recipe=obj, status=RecipePurchase.Status.COMPLETED).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    steps = RecipeStepSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=FeedTag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Recipe
        fields = [
            "slug",
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
            "premium_content",
            "is_premium",
            "price",
            "currency",
            "tags",
            "steps",
        ]

    def create(self, validated_data: Dict[str, Any]) -> Recipe:
        steps_data = validated_data.pop("steps", [])
        tags = validated_data.pop("tags", [])
        recipe = Recipe.objects.create(author=self.context["request"].user, **validated_data)
        if tags:
            recipe.tags.set(tags)
        for index, step in enumerate(steps_data, start=1):
            step.pop("id", None)
            RecipeStep.objects.create(recipe=recipe, order=index, **step)
        return recipe

    def update(self, instance: Recipe, validated_data: Dict[str, Any]) -> Recipe:
        steps_data = validated_data.pop("steps", None)
        tags = validated_data.pop("tags", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data.keys()))
        if tags is not None:
            instance.tags.set(tags)
        if steps_data is not None:
            instance.steps.all().delete()
            for index, step in enumerate(steps_data, start=1):
                step.pop("id", None)
                RecipeStep.objects.create(recipe=instance, order=index, **step)
        return instance


class DealOfferSerializer(serializers.ModelSerializer):
    tags = FeedTagSerializer(many=True, read_only=True)

    class Meta:
        model = DealOffer
        fields = [
            "id",
            "external_id",
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
            "tags",
        ]


class RecipePurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipePurchase
        fields = ["id", "recipe", "amount", "currency", "status", "provider", "metadata", "created_at"]
        read_only_fields = ["status", "provider", "metadata", "created_at"]


class FeedEventSerializer(serializers.Serializer):
    """Serializer for outbound realtime events."""

    group = serializers.CharField()
    payload = serializers.JSONField()


class NewsArticleEventSerializer(serializers.ModelSerializer):
    tags = FeedTagSerializer(many=True, read_only=True)
    published_at_msk = serializers.SerializerMethodField()
    timezone_label = serializers.SerializerMethodField()

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "source_id",
            "title",
            "lead",
            "body",
            "title_orig",
            "lead_orig",
            "body_orig",
            "lang",
            "translated",
            "translation_provider",
            "source_name",
            "source_url",
            "published_at",
            "published_at_msk",
            "timezone_label",
            "preview_image_url",
            "tonality",
            "source_categories",
            "toxicity_score",
            "clickbait_score",
            "is_flagged",
            "ingested_at",
            "ingestion_source",
            "ingestion_rid",
            "ingestion_metadata",
            "created_at",
            "updated_at",
            "tags",
        ]

    def get_published_at_msk(self, obj: NewsArticle) -> str | None:
        return _format_msk_iso(obj.published_at)

    def get_timezone_label(self, obj: NewsArticle) -> str:
        return "MSK"


class RecipeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = [
            "id",
            "slug",
            "title",
            "short_description",
            "hero_image",
            "cook_time_minutes",
            "is_premium",
            "price",
            "currency",
            "purchases_count",
        ]


class DealOfferEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealOffer
        fields = [
            "id",
            "title",
            "product_name",
            "network",
            "city",
            "price_before",
            "price_after",
            "discount_percent",
            "valid_until",
        ]


def _format_msk_iso(value):
    dt = to_moscow(value)
    return dt.isoformat() if dt else None