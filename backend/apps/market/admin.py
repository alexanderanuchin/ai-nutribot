from __future__ import annotations

from django.contrib import admin

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


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "is_active", "is_verified", "created_at")
    list_filter = ("is_active", "is_verified", "city")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "store", "price", "currency", "is_published", "published_at")
    list_filter = ("is_published", "currency", "store")
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("store",)


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1
    ordering = ("order",)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ("product",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "store", "author", "is_public", "published_at")
    list_filter = ("is_public", "store")
    search_fields = ("title", "slug", "summary")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("store", "author")
    inlines = [RecipeStepInline, RecipeIngredientInline]


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "reserved", "reorder_threshold", "available", "updated_at")
    list_filter = ("product__store",)
    search_fields = ("product__title", "product__slug")
    autocomplete_fields = ("product",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "store", "status", "currency", "updated_at")
    list_filter = ("status", "currency")
    search_fields = ("user__email", "user__username", "store__name")
    autocomplete_fields = ("user", "store")
    inlines = [CartItemInline]


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "goal",
        "start_date",
        "duration_days",
        "total_calories",
        "is_published",
    )
    list_filter = ("is_published", "goal")
    search_fields = ("title", "user__email", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = (
        "duration_days",
        "total_calories",
        "calories_per_day",
        "published_at",
        "created_at",
        "updated_at",
    )


@admin.register(MealPlanItem)
class MealPlanItemAdmin(admin.ModelAdmin):
    list_display = ("meal_plan", "scheduled_for", "meal_type", "recipe", "product", "servings")
    list_filter = ("meal_type",)
    search_fields = ("meal_plan__title", "recipe__title", "product__title")
    autocomplete_fields = ("meal_plan", "recipe", "product")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "price_snapshot", "added_at")
    list_filter = ("cart__status",)
    search_fields = ("cart__user__email", "product__title")
    autocomplete_fields = ("cart", "product")