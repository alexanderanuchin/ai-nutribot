# backend/apps/users/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ProfileViewSet,
    MeViewSet,
    RegisterView,
    CheckPhoneView,
    CheckEmailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PhoneEmailTokenObtainPairView,
)
from .tg_auth import tg_exchange
from .telegram_integration import (
    TelegramBridgeSendView,
    TelegramBridgeStreamView,
    TelegramLinkStartView,
    TelegramStatusView,
)

router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")

me_endpoint = MeViewSet.as_view({"get": "me"})
me_update = MeViewSet.as_view({"patch": "update_profile"})

urlpatterns = [
    # JWT auth
    path("auth/token/", PhoneEmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/check-phone/", CheckPhoneView.as_view(), name="check-phone"),
    path("auth/check-email/", CheckEmailView.as_view(), name="check-email"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("auth/tg_exchange/", tg_exchange, name="tg-exchange"),

    # Telegram integration
    path(
        "integrations/telegram/link/start/",
        TelegramLinkStartView.as_view(),
        name="telegram-link-start",
    ),
    path(
        "integrations/telegram/status/",
        TelegramStatusView.as_view(),
        name="telegram-status",
    ),
    path("telegram/bridge/send/", TelegramBridgeSendView.as_view(), name="telegram-bridge-send"),
    path(
        "telegram/bridge/stream/",
        TelegramBridgeStreamView.as_view(),
        name="telegram-bridge-stream",
    ),

    # Router + "me" ручки
    path("", include(router.urls)),
    path("me/", me_endpoint, name="me"),
    path("me/profile/", me_endpoint, name="me-profile"),
    path("me/profile/update/", me_update, name="me-profile-update"),
]
