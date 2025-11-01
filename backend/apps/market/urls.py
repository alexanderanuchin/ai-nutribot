from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import CartSubmissionView, MarketEventStreamView, MealPlanSubmissionView
from .views import (
    CartItemViewSet,
    CartViewSet,
    InventoryViewSet,
    MarketSearchView,
    MealPlanItemViewSet,
    MealPlanViewSet,
    ProductViewSet,
    RecipeIngredientViewSet,
    RecipeStepViewSet,
    RecipeViewSet,
    StoreViewSet,
)

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
    path("cart/", CartSubmissionView.as_view(), name="market-cart-submit"),
    path("plan/", MealPlanSubmissionView.as_view(), name="market-plan-submit"),
    path("events/", MarketEventStreamView.as_view(), name="market-events"),
    path("search/", MarketSearchView.as_view(), name="market-search"),
    path("", include(router.urls)),
]