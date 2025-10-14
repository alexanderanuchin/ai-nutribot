from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CardWebhookView,
    CheckoutView,
    ComposeRecipePurchaseView,
    OrderViewSet,
    SubscriptionAutopayToggleView,
    SubscriptionChargeView,
    TelegramBotPaymentReportView,
    TelegramStarsInvoiceView,
    WalletBalancesView,
    WalletManualStarsTopUpView,
    WalletSummaryView,
    WalletTopUpView,
    WalletTransactionViewSet,
)

router = DefaultRouter()
router.register("wallet/transactions", WalletTransactionViewSet, basename="wallet-transaction")
router.register("wallet/orders", OrderViewSet, basename="wallet-order")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("wallet/summary/", WalletSummaryView.as_view(), name="wallet-summary"),
    path("wallet/balances/", WalletBalancesView.as_view(), name="wallet-balances"),
    path("wallet/topup/", WalletTopUpView.as_view(), name="wallet-topup"),
    path(
        "wallet/telegram-stars/invoice/",
        TelegramStarsInvoiceView.as_view(),
        name="wallet-telegram-stars-invoice",
    ),
    path("wallet/manual-stars/", WalletManualStarsTopUpView.as_view(), name="wallet-manual-stars"),
    path(
        "bot/telegram-stars/payment/",
        TelegramBotPaymentReportView.as_view(),
        name="bot-telegram-stars-payment",
    ),
    path("orders/checkout/", CheckoutView.as_view(), name="orders-checkout"),
    path(
        "subscriptions/<int:subscription_id>/enable_autopay/",
        SubscriptionAutopayToggleView.as_view(),
        {"action": "enable"},
        name="subscription-enable-autopay",
    ),
    path(
        "subscriptions/<int:subscription_id>/disable_autopay/",
        SubscriptionAutopayToggleView.as_view(),
        {"action": "disable"},
        name="subscription-disable-autopay",
    ),
    path(
        "subscriptions/<int:subscription_id>/charge/",
        SubscriptionChargeView.as_view(),
        name="subscription-charge",
    ),
    path(
        "features/compose_recipe/purchase/",
        ComposeRecipePurchaseView.as_view(),
        name="feature-compose-recipe-purchase",
    ),
    path(
        "webhooks/payments/card/",
        CardWebhookView.as_view(),
        name="webhook-card",
    ),
    path("", include(router.urls)),
]