from __future__ import annotations

from typing import Any, Iterable, Optional

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


def _flatten_metadata_value(metadata: Optional[dict[str, Any]], key: str, default: Any = None) -> Any:
    if not metadata:
        return default
    return metadata.get(key, default)


def _ensure_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN check
        return None
    return number


class StoreSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    owner_full_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    tags = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    delivery_eta_minutes = serializers.SerializerMethodField()
    delivery_price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    link_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            "id",
            "owner",
            "owner_username",
            "owner_full_name",
            "name",
            "slug",
            "description",
            "city",
            "logo_url",
            "is_active",
            "is_verified",
            "metadata",
            "tags",
            "rating",
            "rating_count",
            "delivery_eta_minutes",
            "delivery_price",
            "currency",
            "hero_image_url",
            "link_url",
            "is_online",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_username",
            "owner_full_name",
            "is_verified",
            "metadata",
            "tags",
            "rating",
            "rating_count",
            "delivery_eta_minutes",
            "delivery_price",
            "currency",
            "hero_image_url",
            "link_url",
            "is_online",
            "created_at",
            "updated_at",
        ]

    def get_tags(self, obj: Store) -> list[str]:
        tags: Iterable[str] | None = _flatten_metadata_value(obj.metadata, "tags")
        if not tags:
            return []
        return [str(tag) for tag in tags if isinstance(tag, str)]

    def get_rating(self, obj: Store) -> Optional[float]:
        return _ensure_number(_flatten_metadata_value(obj.metadata, "rating"))

    def get_rating_count(self, obj: Store) -> Optional[int]:
        value = _flatten_metadata_value(obj.metadata, "rating_count")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_delivery_eta_minutes(self, obj: Store) -> Optional[int]:
        value = _flatten_metadata_value(obj.metadata, "delivery_eta_minutes")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_delivery_price(self, obj: Store) -> Optional[float]:
        return _ensure_number(_flatten_metadata_value(obj.metadata, "delivery_price"))

    def get_currency(self, obj: Store) -> Optional[str]:
        currency = _flatten_metadata_value(obj.metadata, "currency")
        if currency:
            return str(currency)
        return None

    def get_hero_image_url(self, obj: Store) -> Optional[str]:
        hero = _flatten_metadata_value(obj.metadata, "hero_image_url")
        return str(hero) if hero else None

    def get_link_url(self, obj: Store) -> Optional[str]:
        link = _flatten_metadata_value(obj.metadata, "link_url")
        return str(link) if link else None

    def get_is_online(self, obj: Store) -> bool:
        value = _flatten_metadata_value(obj.metadata, "is_online")
        return bool(value)


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
    store_name = serializers.CharField(source="store.name", read_only=True)
    store_slug = serializers.CharField(source="store.slug", read_only=True)
    store_city = serializers.CharField(source="store.city", read_only=True)
    store_logo_url = serializers.CharField(source="store.logo_url", read_only=True)
    store_is_verified = serializers.BooleanField(source="store.is_verified", read_only=True)
    store_owner_id = serializers.IntegerField(source="store.owner_id", read_only=True)
    inventory = InventorySerializer(read_only=True)
    inventory_available = serializers.IntegerField(source="inventory.available", read_only=True)
    inventory_quantity = serializers.IntegerField(source="inventory.quantity", read_only=True)
    inventory_reserved = serializers.IntegerField(source="inventory.reserved", read_only=True)
    subtitle = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    price_original = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
            "store_name",
            "store_slug",
            "store_city",
            "store_logo_url",
            "store_is_verified",
            "store_owner_id",
            "title",
            "slug",
            "description",
            "price",
            "currency",
            "weight_grams",
            "tags",
            "nutrition",
            "metadata",
            "subtitle",
            "image_url",
            "brand",
            "unit",
            "price_original",
            "discount_percent",
            "badges",
            "rating",
            "rating_count",
            "available",
            "is_published",
            "published_at",
            "available_from",
            "available_until",
            "created_at",
            "updated_at",
            "inventory",
            "inventory_available",
            "inventory_quantity",
            "inventory_reserved",
        ]
        read_only_fields = [
            "id",
            "store_name",
            "store_slug",
            "store_city",
            "store_logo_url",
            "store_is_verified",
            "store_owner_id",
            "published_at",
            "created_at",
            "updated_at",
            "inventory",
            "inventory_available",
            "inventory_quantity",
            "inventory_reserved",
            "subtitle",
            "image_url",
            "brand",
            "unit",
            "price_original",
            "discount_percent",
            "badges",
            "rating",
            "rating_count",
            "available",
        ]
        extra_kwargs = {
            "price": {"coerce_to_string": False},
        }

    def get_subtitle(self, obj: Product) -> Optional[str]:
        subtitle = _flatten_metadata_value(obj.metadata, "subtitle")
        return str(subtitle) if subtitle else None

    def get_image_url(self, obj: Product) -> Optional[str]:
        image = _flatten_metadata_value(obj.metadata, "image_url")
        return str(image) if image else None

    def get_brand(self, obj: Product) -> Optional[str]:
        brand = _flatten_metadata_value(obj.metadata, "brand")
        return str(brand) if brand else None

    def get_unit(self, obj: Product) -> Optional[str]:
        unit = _flatten_metadata_value(obj.metadata, "unit")
        if unit:
            return str(unit)
        if obj.weight_grams:
            return f"{obj.weight_grams} г"
        return None

    def get_price_original(self, obj: Product) -> Optional[float]:
        value = _flatten_metadata_value(obj.metadata, "price_original")
        return _ensure_number(value)

    def get_discount_percent(self, obj: Product) -> Optional[float]:
        value = _flatten_metadata_value(obj.metadata, "discount_percent")
        return _ensure_number(value)

    def get_badges(self, obj: Product) -> list[str]:
        badges: Iterable[str] | None = _flatten_metadata_value(obj.metadata, "badges")
        if badges:
            return [str(badge) for badge in badges if isinstance(badge, str)]
        return [tag for tag in obj.tags if isinstance(tag, str)]

    def get_rating(self, obj: Product) -> Optional[float]:
        value = _flatten_metadata_value(obj.metadata, "rating")
        return _ensure_number(value)

    def get_rating_count(self, obj: Product) -> Optional[int]:
        value = _flatten_metadata_value(obj.metadata, "rating_count")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_available(self, obj: Product) -> bool:
        inventory = getattr(obj, "inventory", None)
        if not inventory:
            return False
        return inventory.available > 0


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
    store_name = serializers.CharField(source="store.name", read_only=True)
    store_slug = serializers.CharField(source="store.slug", read_only=True)
    store_city = serializers.CharField(source="store.city", read_only=True)
    store_logo_url = serializers.CharField(source="store.logo_url", read_only=True)
    subtitle = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    calories = serializers.SerializerMethodField()
    protein_g = serializers.SerializerMethodField()
    fat_g = serializers.SerializerMethodField()
    carbs_g = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()
    is_in_plan = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "store",
            "store_name",
            "store_slug",
            "store_city",
            "store_logo_url",
            "author",
            "title",
            "slug",
            "summary",
            "subtitle",
            "description",
            "cooking_time_minutes",
            "servings",
            "difficulty",
            "hero_image_url",
            "preview_image_url",
            "calories",
            "protein_g",
            "fat_g",
            "carbs_g",
            "price",
            "currency",
            "rating",
            "rating_count",
            "tags",
            "is_premium",
            "is_in_plan",
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
            "store_name",
            "store_slug",
            "store_city",
            "store_logo_url",
            "published_at",
            "created_at",
            "updated_at",
            "steps",
            "ingredients",
            "subtitle",
            "description",
            "hero_image_url",
            "preview_image_url",
            "calories",
            "protein_g",
            "fat_g",
            "carbs_g",
            "price",
            "currency",
            "rating",
            "rating_count",
            "tags",
            "is_premium",
            "is_in_plan",
        ]

    def _recipe_metadata(self, obj: Recipe) -> dict[str, Any]:
        return obj.metadata or {}

    def get_subtitle(self, obj: Recipe) -> Optional[str]:
        metadata = self._recipe_metadata(obj)
        subtitle = metadata.get("subtitle")
        return str(subtitle) if subtitle else None

    def get_description(self, obj: Recipe) -> Optional[str]:
        if obj.summary:
            return obj.summary
        metadata = self._recipe_metadata(obj)
        description = metadata.get("description")
        return str(description) if description else None

    def get_hero_image_url(self, obj: Recipe) -> Optional[str]:
        metadata = self._recipe_metadata(obj)
        image = metadata.get("hero_image_url")
        return str(image) if image else None

    def get_preview_image_url(self, obj: Recipe) -> Optional[str]:
        metadata = self._recipe_metadata(obj)
        image = metadata.get("preview_image_url")
        if image:
            return str(image)
        return self.get_hero_image_url(obj)

    def _nutrition_value(self, obj: Recipe, key: str) -> float:
        metadata = self._recipe_metadata(obj)
        nutrition = metadata.get("nutrition") or {}
        value = nutrition.get(key)
        number = _ensure_number(value)
        return number if number is not None else 0.0

    def get_calories(self, obj: Recipe) -> float:
        return self._nutrition_value(obj, "calories")

    def get_protein_g(self, obj: Recipe) -> float:
        return self._nutrition_value(obj, "protein_g")

    def get_fat_g(self, obj: Recipe) -> float:
        return self._nutrition_value(obj, "fat_g")

    def get_carbs_g(self, obj: Recipe) -> float:
        return self._nutrition_value(obj, "carbs_g")

    def get_price(self, obj: Recipe) -> Optional[float]:
        metadata = self._recipe_metadata(obj)
        price = metadata.get("price")
        if isinstance(price, dict):
            return _ensure_number(price.get("value"))
        return _ensure_number(price)

    def get_currency(self, obj: Recipe) -> Optional[str]:
        metadata = self._recipe_metadata(obj)
        price = metadata.get("price")
        if isinstance(price, dict):
            currency = price.get("currency")
            return str(currency) if currency else None
        currency = metadata.get("currency")
        return str(currency) if currency else None

    def get_rating(self, obj: Recipe) -> Optional[float]:
        metadata = self._recipe_metadata(obj)
        return _ensure_number(metadata.get("rating"))

    def get_rating_count(self, obj: Recipe) -> Optional[int]:
        metadata = self._recipe_metadata(obj)
        value = metadata.get("rating_count")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_tags(self, obj: Recipe) -> list[str]:
        metadata = self._recipe_metadata(obj)
        tags: Iterable[str] | None = metadata.get("tags")
        if not tags:
            return []
        return [str(tag) for tag in tags if isinstance(tag, str)]

    def get_is_premium(self, obj: Recipe) -> bool:
        metadata = self._recipe_metadata(obj)
        return bool(metadata.get("is_premium"))

    def get_is_in_plan(self, obj: Recipe) -> bool:
        request = self.context.get("request") if self.context else None
        if not request or not request.user.is_authenticated:
            return False
        plan_ids = getattr(request, "_market_plan_recipe_ids", None)
        if plan_ids is None:
            return False
        return obj.id in plan_ids


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
        extra_kwargs = {
            "price_snapshot": {"required": False, "coerce_to_string": False},
        }


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