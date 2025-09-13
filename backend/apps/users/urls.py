from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, MeViewSet

router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")

me_profile = MeViewSet.as_view({"get": "profile"})
me_update = MeViewSet.as_view({"patch": "update_profile"})
me_user = MeViewSet.as_view({"get": "user"})

urlpatterns = [
    path("", include(router.urls)),
    path("me/profile/", me_profile, name="me-profile"),
    path("me/profile/update/", me_update, name="me-profile-update"),
    path("me/user/", me_user, name="me-user"),
]
