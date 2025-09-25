from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet, catalog_health

router = DefaultRouter()
router.register(r"items", MenuItemViewSet, basename="items")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", catalog_health, name="catalog-health"),
]
