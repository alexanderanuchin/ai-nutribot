from django.contrib import admin
from django.urls import include, path, re_path

# Health & metrics endpoints
from health import healthz, readyz, metrics as metrics_view
from apps.users.views import BotStarsBalanceView, StarsBalanceView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Observability
    re_path(r"^healthz/?$", healthz, name="healthz"),
    re_path(r"^readyz/?$", readyz, name="readyz"),
    # Map both /metrics and /metrics/ to the same view (no redirect quirks)
    re_path(r"^metrics/?$", metrics_view, name="metrics"),

    # API
    path("api/auth/", include("apps.auth.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/nutrition/", include("apps.nutrition.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/monitoring/", include("apps.monitoring.urls")),
    path("api/v1/", include("apps.feed.urls")),
    path("api/v1/market/", include("apps.market.urls")),
    path("api/reviews/", include("apps.reviews.urls")),

    # Wallet endpoints
    path("api/me/stars/", StarsBalanceView.as_view(), name="api-me-stars"),
    path("api/admin/stars/bot-balance/", BotStarsBalanceView.as_view(), name="api-bot-stars-balance"),
]
