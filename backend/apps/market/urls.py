from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CartItemViewSet,
    CartViewSet,
    InventoryViewSet,
    MealPlanItemViewSet,
    MealPlanViewSet,
    ProductViewSet,
    RecipeIngredientViewSet,
    RecipeStepViewSet,
    RecipeViewSet,
    StoreViewSet,
)
from .views_events import MarketEventsView

app_name = "market"

router = DefaultRouter()
router.register("stores", StoreViewSet, basename="market-store")
router.register("products", ProductViewSet, basename="market-product")
router.register("recipes", RecipeViewSet, basename="market-recipe")
router.register("recipe-steps", RecipeStepViewSet, basename="market-recipe-step")
router.register("recipe-ingredients", RecipeIngredientViewSet, basename="market-recipe-ingredient")
router.register("inventory", InventoryViewSet, basename="market-inventory")
router.register("carts", CartViewSet, basename="market-cart")
router.register("cart-items", CartItemViewSet, basename="market-cart-item")
router.register("meal-plans", MealPlanViewSet, basename="market-meal-plan")
router.register("meal-plan-items", MealPlanItemViewSet, basename="market-meal-plan-item")

urlpatterns = [
    path("", include(router.urls)),
    path("events/", MarketEventsView.as_view(), name="market-events"),
]