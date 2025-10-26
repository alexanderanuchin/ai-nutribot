from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DealIngestView,
    FeedEventStreamView,
    FeedView,
    NewsArticleDetailView,
    NewsIngestView,
    RecipeViewSet,
)


router = DefaultRouter()
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("feed/", FeedView.as_view(), name="feed-list"),
    path("feed/events/", FeedEventStreamView.as_view(), name="feed-events"),
    path("feed/news/<int:pk>/", NewsArticleDetailView.as_view(), name="feed-news-detail"),
    path("feed/news/ingest/", NewsIngestView.as_view(), name="feed-news-ingest"),
    path("feed/deals/ingest/", DealIngestView.as_view(), name="feed-deals-ingest"),
    path("", include(router.urls)),
]