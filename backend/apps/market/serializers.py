from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers


from .models import (
    Cart,
    CartItem,
    Inventory,
    MealPlan,
    MealPlanItem,
    Product,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    Store,
)

User = get_user_model()


class StoreSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Store
        fields = [
            "id",
            "owner",
            "name",
            "slug",
            "description",
            "city",
            "logo_url",
            "is_active",
            "is_verified",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_verified", "created_at", "updated_at"]


class InventorySerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "quantity",
            "reserved",
            "reorder_threshold",
            "available",
            "updated_at",
        ]
        read_only_fields = ["id", "available", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
            "title",
            "slug",
            "description",
            "price",
            "currency",
            "weight_grams",
            "tags",
            "nutrition",
            "metadata",
            "is_published",
            "published_at",
            "available_from",
            "available_until",
            "created_at",
            "updated_at",
            "inventory",
        ]
        read_only_fields = ["id", "published_at", "created_at", "updated_at", "inventory"]


class RecipeStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeStep
        fields = [
            "id",
            "recipe",
            "order",
            "title",
            "instructions",
            "media_url",
        ]
        read_only_fields = ["id"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = [
            "id",
            "recipe",
            "product",
            "name",
            "quantity",
            "unit",
            "notes",
        ]
        read_only_fields = ["id"]


class RecipeSerializer(serializers.ModelSerializer):
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    steps = RecipeStepSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "store",
            "author",
            "title",
            "slug",
            "summary",
            "cooking_time_minutes",
            "servings",
            "difficulty",
            "is_public",
            "published_at",
            "metadata",
            "created_at",
            "updated_at",
            "steps",
            "ingredients",
        ]
        read_only_fields = [
            "id",
            "published_at",
            "created_at",
            "updated_at",
            "steps",
            "ingredients",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "quantity",
            "price_snapshot",
            "metadata",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]
        extra_kwargs = {"price_snapshot": {"required": False}}


class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "user",
            "store",
            "status",
            "currency",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "items"]


class MealPlanItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlanItem
        fields = [
            "id",
            "meal_plan",
            "recipe",
            "product",
            "servings",
            "scheduled_for",
            "meal_type",
            "notes",
        ]
        read_only_fields = ["id"]


class MarketSearchResultSerializer(serializers.Serializer):
    resource = serializers.ChoiceField(choices=["recipes", "products", "stores"])
    id = serializers.IntegerField()
    title = serializers.CharField()
    subtitle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    metrics = serializers.DictField(child=serializers.JSONField(), required=False)
    preview = serializers.DictField(child=serializers.JSONField(), required=False)


class MarketSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    resource = serializers.ChoiceField(choices=["all", "recipes", "products", "stores"])
    total = serializers.IntegerField()
    results = MarketSearchResultSerializer(many=True)
    facets = serializers.DictField(child=serializers.ListField(child=serializers.DictField()))
    suggestions = serializers.DictField()


class MarketSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    resource = serializers.ChoiceField(choices=["all", "recipes", "products", "stores"], default="all")
    limit = serializers.IntegerField(required=False, min_value=1, max_value=30, default=12)

    def validate(self, attrs):
        attrs.setdefault("filters", {})
        request = self.context.get("request")
        if request:
            filters = {}
            for key, value in request.query_params.items():
                if key in {"q", "resource", "limit"}:
                    continue
                filters[key] = value
            attrs["filters"] = filters
        return attrs


class MealPlanSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = MealPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = MealPlan
        fields = [
            "id",
            "user",
            "title",
            "description",
            "start_date",
            "end_date",
            "is_published",
            "published_at",
            "metadata",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "user",
            "published_at",
            "created_at",
            "updated_at",
            "items",
        ]