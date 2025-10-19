from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from django.db.models import Count, F
from rest_framework import serializers

from .models import DealOffer, FeedTag, NewsArticle, Recipe, RecipePurchase, RecipeReaction, RecipeStep


class FeedTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedTag
        fields = ["id", "name", "slug", "kind"]


class NewsArticleSerializer(serializers.ModelSerializer):
    tags = FeedTagSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "source_id",
            "title",
            "lead",
            "source_name",
            "source_url",
            "published_at",
            "preview_image_url",
            "tags",
        ]


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
            "premium_content",
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
    class Meta:
        model = NewsArticle
        fields = ["id", "title", "lead", "source_name", "source_url", "published_at", "preview_image_url"]


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