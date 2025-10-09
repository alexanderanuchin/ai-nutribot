from django.contrib import admin
from django.urls import include, path

from apps.users.views import BotStarsBalanceView, StarsBalanceView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.auth.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/nutrition/", include("apps.nutrition.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/me/stars/", StarsBalanceView.as_view(), name="api-me-stars"),
    path("api/admin/stars/bot-balance/", BotStarsBalanceView.as_view(), name="api-bot-stars-balance"),
]
