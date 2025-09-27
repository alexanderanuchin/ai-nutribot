from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, WalletSummaryView, WalletTransactionViewSet

router = DefaultRouter()
router.register("wallet/transactions", WalletTransactionViewSet, basename="wallet-transaction")
router.register("wallet/orders", OrderViewSet, basename="wallet-order")

urlpatterns = [
    path("wallet/summary/", WalletSummaryView.as_view(), name="wallet-summary"),
    path("", include(router.urls)),
]