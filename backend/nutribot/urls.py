from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/nutrition/", include("apps.nutrition.urls")),
    path("api/orders/", include("apps.orders.urls")),
]
