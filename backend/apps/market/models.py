from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Store(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="market_stores",
    )
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        indexes = [
            models.Index(fields=["slug"], name="market_store_slug"),
            models.Index(fields=["owner", "is_active"], name="market_store_owner_active"),
            GinIndex(fields=["metadata"], name="market_store_metadata_gin", opclasses=["jsonb_path_ops"]),
        ]
        permissions = [
            ("manage_market", "Can manage marketplace resources"),
            ("moderate_market", "Can moderate marketplace content"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Store<{self.slug}>"


class Product(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="products",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default="RUB")
    weight_grams = models.PositiveIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    nutrition = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "id")
        verbose_name = "Product"
        verbose_name_plural = "Products"
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="market_product_store_slug"),
        ]
        indexes = [
            models.Index(fields=["slug"], name="market_product_slug"),
            models.Index(fields=["store", "is_published"], name="market_product_store_pub"),
            models.Index(fields=["is_published", "published_at"], name="market_product_published"),
            GinIndex(fields=["metadata"], name="market_product_metadata_gin", opclasses=["jsonb_path_ops"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Product<{self.store_id}:{self.slug}>"

    def mark_published(self) -> None:
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()


class Recipe(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="market_recipes",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    summary = models.TextField(blank=True)
    cooking_time_minutes = models.PositiveIntegerField(default=0)
    servings = models.PositiveIntegerField(default=1)
    difficulty = models.CharField(max_length=32, blank=True)
    is_public = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "id")
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="market_recipe_store_slug"),
        ]
        indexes = [
            models.Index(fields=["slug"], name="market_recipe_slug"),
            models.Index(fields=["store", "is_public"], name="market_recipe_store_public"),
            models.Index(fields=["published_at"], name="market_recipe_published"),
            GinIndex(fields=["metadata"], name="market_recipe_metadata_gin", opclasses=["jsonb_path_ops"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Recipe<{self.store_id}:{self.slug}>"


class RecipeStep(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255, blank=True)
    instructions = models.TextField()
    media_url = models.URLField(blank=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Recipe step"
        verbose_name_plural = "Recipe steps"
        constraints = [
            models.UniqueConstraint(fields=["recipe", "order"], name="market_recipestep_order"),
        ]
        indexes = [
            models.Index(fields=["recipe", "order"], name="market_recipe_step_order"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"RecipeStep<{self.recipe_id}:{self.order}>"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingredient_usages",
    )
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    unit = models.CharField(max_length=64, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("id",)
        verbose_name = "Recipe ingredient"
        verbose_name_plural = "Recipe ingredients"
        indexes = [
            models.Index(fields=["recipe"], name="market_recipe_ing_rec"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"RecipeIngredient<{self.recipe_id}:{self.name}>"


class Inventory(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    reorder_threshold = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory"
        verbose_name_plural = "Inventory"
        indexes = [
            models.Index(fields=["quantity", "reserved"], name="market_inventory_stock"),
        ]
        permissions = [
            ("manage_inventory", "Can manage inventory"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Inventory<{self.product_id}>"

    @property
    def available(self) -> int:
        return max(0, self.quantity - self.reserved)


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CHECKED_OUT = "checked_out", "Checked out"
        ABANDONED = "abandoned", "Abandoned"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="market_carts",
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    currency = models.CharField(max_length=3, default="RUB")
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "store"],
                condition=models.Q(status="active"),
                name="market_cart_unique_active_per_store",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="market_cart_user_status"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Cart<{self.user_id}:{self.store_id}:{self.status}>"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    metadata = models.JSONField(default=dict, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart item"
        verbose_name_plural = "Cart items"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="market_cartitem_cart_product"),
        ]
        indexes = [
            models.Index(fields=["cart"], name="market_cartitem_cart"),
            models.Index(fields=["product"], name="market_cartitem_product"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"CartItem<{self.cart_id}:{self.product_id}>"


class MealPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meal_plans",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_date", "id")
        verbose_name = "Meal plan"
        verbose_name_plural = "Meal plans"
        indexes = [
            models.Index(fields=["user", "start_date"], name="market_mealplan_user_start"),
            models.Index(fields=["is_published", "published_at"], name="market_mealplan_published"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"MealPlan<{self.user_id}:{self.title}>"


class MealPlanItem(models.Model):
    meal_plan = models.ForeignKey(
        MealPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_plan_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_plan_items",
    )
    servings = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))
    scheduled_for = models.DateField(null=True, blank=True)
    meal_type = models.CharField(max_length=32, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Meal plan item"
        verbose_name_plural = "Meal plan items"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(recipe__isnull=False) | models.Q(product__isnull=False)
                ),
                name="market_mealplanitem_requires_reference",
            ),
            models.UniqueConstraint(
                fields=["meal_plan", "scheduled_for", "meal_type", "recipe", "product"],
                name="market_mealplanitem_unique_slot",
            ),
        ]
        indexes = [
            models.Index(fields=["meal_plan"], name="market_mealplanitem_plan"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"MealPlanItem<{self.meal_plan_id}>"