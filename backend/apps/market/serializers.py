from __future__ import annotations

from typing import Any, Iterable, Optional

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.orders.models import Order
from apps.users.models import Profile

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
from .services import (
    get_meal_plan_price_stars,
    get_recipe_price_stars,
    has_meal_plan_access,
    has_recipe_access,
    is_recipe_premium,
)
from .services.meal_plan_metrics import (
    add_nutrition,
    aggregate_plan_nutrition,
    empty_nutrition,
    format_nutrition,
    item_base_nutrition,
    item_total_nutrition,
    product_nutrition,
    recipe_nutrition,
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


def _resolve_profile(context: dict | None) -> Profile | None:
    if not context:
        return None
    request = context.get("request")
    if not request or not getattr(request.user, "is_authenticated", False):
        return None
    cached = getattr(request, "_market_profile", None)
    if isinstance(cached, Profile):
        return cached
    profile = getattr(request.user, "profile", None)
    if isinstance(profile, Profile):
        setattr(request, "_market_profile", profile)
        return profile
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return None
    setattr(request, "_market_profile", profile)
    return profile


def _recipe_metadata(recipe: "Recipe") -> dict[str, Any]:
    metadata = recipe.metadata or {}
    if isinstance(metadata, dict):
        return metadata
    return {}


def _product_metadata(product: "Product") -> dict[str, Any]:
    metadata = product.metadata or {}
    if isinstance(metadata, dict):
        return metadata
    return {}


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
    price_stars = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()
    is_free = serializers.SerializerMethodField()
    is_in_plan = serializers.SerializerMethodField()
    has_access = serializers.SerializerMethodField()

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
            "price_stars",
            "currency",
            "rating",
            "rating_count",
            "tags",
            "is_premium",
            "is_free",
            "is_in_plan",
            "has_access",
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
            "price_stars",
            "currency",
            "rating",
            "rating_count",
            "tags",
            "is_premium",
            "is_free",
            "is_in_plan",
            "has_access",
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
        stars = get_recipe_price_stars(obj)
        if stars is not None:
            return float(stars)
        metadata = self._recipe_metadata(obj)
        price = metadata.get("price")
        if isinstance(price, dict):
            return _ensure_number(price.get("value"))
        return _ensure_number(price)

    def get_price_stars(self, obj: Recipe) -> Optional[int]:
        stars = get_recipe_price_stars(obj)
        return int(stars) if stars is not None else None

    def get_currency(self, obj: Recipe) -> Optional[str]:
        stars = get_recipe_price_stars(obj)
        if stars is not None:
            return "STARS"
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
        if metadata.get("is_premium"):
            return True
        return get_recipe_price_stars(obj) is not None

    def get_is_free(self, obj: Recipe) -> bool:
        return not self.get_is_premium(obj)

    def get_is_in_plan(self, obj: Recipe) -> bool:
        request = self.context.get("request") if self.context else None
        if not request or not request.user.is_authenticated:
            return False
        plan_ids = getattr(request, "_market_plan_recipe_ids", None)
        if plan_ids is None:
            return False
        return obj.id in plan_ids

    def get_has_access(self, obj: Recipe) -> bool:
        profile = _resolve_profile(self.context)
        if profile is None:
            return not self.get_is_premium(obj)
        return has_recipe_access(profile, obj)


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


class CartCheckoutSerializer(serializers.Serializer):
    pay_with_wallet = serializers.BooleanField(required=False, default=False)
    wallet_currency = serializers.CharField(required=False, allow_blank=False)
    metadata = serializers.JSONField(required=False)

    def validate_wallet_currency(self, value: str) -> str:
        normalized = value.upper()
        allowed = {
            Order.Currency.TELEGRAM_STARS,
            Order.Currency.CALOCOIN,
        }
        if normalized not in allowed:
            raise serializers.ValidationError("Доступны только кошельки Stars или CaloCoin")
        return normalized

    def validate_metadata(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Метаданные должны быть объектом")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        pay_with_wallet = attrs.get("pay_with_wallet", False)
        wallet_currency = attrs.get("wallet_currency")
        if pay_with_wallet and not wallet_currency:
            raise serializers.ValidationError(
                {"wallet_currency": "Укажите валюту кошелька для моментальной оплаты"}
            )
        if not pay_with_wallet and wallet_currency:
            raise serializers.ValidationError(
                {"wallet_currency": "Валюта кошелька используется только при оплате из кошелька"}
            )
        return attrs


class MealPlanItemSerializer(serializers.ModelSerializer):
    recipe_snapshot = serializers.SerializerMethodField()
    product_snapshot = serializers.SerializerMethodField()
    nutrition = serializers.SerializerMethodField()
    total_nutrition = serializers.SerializerMethodField()

    class Meta:
        model = MealPlanItem
        fields = [
            "id",
            "meal_plan",
            "recipe",
            "product",
            "recipe_snapshot",
            "product_snapshot",
            "servings",
            "scheduled_for",
            "meal_type",
            "notes",
            "nutrition",
            "total_nutrition",
        ]
        read_only_fields = [
            "id",
            "recipe_snapshot",
            "product_snapshot",
            "nutrition",
            "total_nutrition",
        ]

    def get_recipe_snapshot(self, obj: MealPlanItem) -> Optional[dict[str, Any]]:
        recipe = obj.recipe
        if not recipe:
            return None
        metadata = _recipe_metadata(recipe)
        preview = metadata.get("preview_image_url") or metadata.get("hero_image_url")
        hero = metadata.get("hero_image_url") or preview
        price_data = metadata.get("price") if isinstance(metadata.get("price"), dict) else None
        price = None
        currency = None
        if price_data:
            price = _ensure_number(price_data.get("value"))
            currency_val = price_data.get("currency")
            currency = str(currency_val) if currency_val else None
        elif metadata.get("price") is not None:
            price = _ensure_number(metadata.get("price"))
        if not currency:
            currency_val = metadata.get("currency")
            currency = str(currency_val) if currency_val else None
        stars = get_recipe_price_stars(recipe)
        price_stars = int(stars) if stars is not None else None
        if price_stars is not None:
            price = float(price_stars)
            currency = "STARS"
        nutrition = recipe_nutrition(recipe)
        return {
            "id": recipe.id,
            "title": recipe.title,
            "slug": recipe.slug,
            "store_id": recipe.store_id,
            "store_name": getattr(recipe.store, "name", None),
            "store_slug": getattr(recipe.store, "slug", None),
            "hero_image_url": str(hero) if hero else None,
            "preview_image_url": str(preview) if preview else None,
            "servings": recipe.servings,
            "cooking_time_minutes": recipe.cooking_time_minutes,
            "calories": nutrition["calories"],
            "protein_g": nutrition["protein_g"],
            "fat_g": nutrition["fat_g"],
            "carbs_g": nutrition["carbs_g"],
            "price": price,
            "currency": currency,
            "price_stars": price_stars,
        }

    def get_product_snapshot(self, obj: MealPlanItem) -> Optional[dict[str, Any]]:
        product = obj.product
        if not product:
            return None
        metadata = _product_metadata(product)
        image = metadata.get("image_url")
        if not image and product.metadata:
            image = product.metadata.get("image")
        nutrition = product_nutrition(product)
        return {
            "id": product.id,
            "title": product.title,
            "slug": product.slug,
            "store_id": product.store_id,
            "store_name": getattr(product.store, "name", None),
            "store_slug": getattr(product.store, "slug", None),
            "price": float(product.price),
            "currency": product.currency,
            "image_url": str(image) if image else None,
            "calories": nutrition["calories"],
            "protein_g": nutrition["protein_g"],
            "fat_g": nutrition["fat_g"],
            "carbs_g": nutrition["carbs_g"],
        }

    def get_nutrition(self, obj: MealPlanItem) -> dict[str, float]:
        return format_nutrition(item_base_nutrition(obj))

    def get_total_nutrition(self, obj: MealPlanItem) -> dict[str, float]:
        return format_nutrition(item_total_nutrition(obj))


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
    nutrition_totals = serializers.SerializerMethodField()
    daily_breakdown = serializers.SerializerMethodField()
    price_stars = serializers.SerializerMethodField()
    has_access = serializers.SerializerMethodField()
    is_free = serializers.SerializerMethodField()

    class Meta:
        model = MealPlan
        fields = [
            "id",
            "user",
            "title",
            "description",
            "start_date",
            "end_date",
            "goal",
            "tags",
            "duration_days",
            "is_published",
            "published_at",
            "price_amount",
            "price_currency",
            "price_stars",
            "is_free",
            "has_access",
            "total_calories",
            "calories_per_day",
            "metadata",
            "created_at",
            "updated_at",
            "items",
            "nutrition_totals",
            "daily_breakdown",
        ]
        read_only_fields = [
            "id",
            "user",
            "duration_days",
            "published_at",
            "created_at",
            "updated_at",
            "items",
            "nutrition_totals",
            "daily_breakdown",
            "price_stars",
            "is_free",
            "has_access",
            "total_calories",
            "calories_per_day",
        ]

    def _get_items(self, obj: MealPlan) -> Iterable[MealPlanItem]:
        if hasattr(obj, "_prefetched_objects_cache") and "items" in obj._prefetched_objects_cache:
            return obj._prefetched_objects_cache["items"]  # type: ignore[index]
        return obj.items.all()

    def _get_aggregate(self, obj: MealPlan) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
        cached = getattr(obj, "_nutrition_aggregate", None)
        if cached is not None:
            return cached
        aggregate_payload = aggregate_plan_nutrition(obj, self._get_items(obj))
        totals = aggregate_payload.totals
        daily = aggregate_payload.daily
        aggregate = (totals, daily)
        setattr(obj, "_nutrition_aggregate", aggregate)
        return aggregate

    def get_nutrition_totals(self, obj: MealPlan) -> dict[str, float]:
        totals, _ = self._get_aggregate(obj)
        return format_nutrition(totals)

    def get_daily_breakdown(self, obj: MealPlan) -> list[dict[str, Any]]:
        _, daily = self._get_aggregate(obj)

        def sort_key(item: tuple[str, dict[str, float]]):
            key, _payload = item
            if key == "unscheduled":
                return (1, "")
            return (0, key)

        breakdown: list[dict[str, Any]] = []
        for key, payload in sorted(daily.items(), key=sort_key):
            breakdown.append(
                {
                    "date": key if key != "unscheduled" else None,
                    "is_unscheduled": key == "unscheduled",
                    "totals": format_nutrition(payload),
                }
            )
        return breakdown

    def get_price_stars(self, obj: MealPlan) -> Optional[int]:
        stars = get_meal_plan_price_stars(obj)
        return int(stars) if stars is not None else None

    def get_is_free(self, obj: MealPlan) -> bool:
        return self.get_price_stars(obj) is None

    def get_has_access(self, obj: MealPlan) -> bool:
        profile = _resolve_profile(self.context)
        if profile is None:
            return self.get_is_free(obj)
        return has_meal_plan_access(profile, obj)