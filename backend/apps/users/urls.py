# backend/apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    ProfileViewSet,
    MeViewSet,
    RegisterView,
    CheckPhoneView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")

me_profile = MeViewSet.as_view({"get": "profile"})
me_update = MeViewSet.as_view({"patch": "update_profile"})
me_user = MeViewSet.as_view({"get": "user"})

urlpatterns = [
    # JWT auth
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/check-phone/", CheckPhoneView.as_view(), name="check-phone"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),

    # Router + "me" ручки
    path("", include(router.urls)),
    path("me/profile/", me_profile, name="me-profile"),
    path("me/profile/update/", me_update, name="me-profile-update"),
    path("me/user/", me_user, name="me-user"),
]
