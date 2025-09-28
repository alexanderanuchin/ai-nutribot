from __future__ import annotations

# Create your views here.
from decimal import Decimal
from typing import Any, Dict

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import (
    DeliveryService,
    DeliveryWindow,
    IntegrationWebhookEvent,
    MealSubscription,
    Order,
    PaymentAttempt,
    WalletTransaction,
)
from apps.orders.serializers import (
    OrderPaymentSerializer,
    OrderSerializer,
    WalletSummarySerializer,
    WalletTopUpSerializer,
    WalletTransactionSerializer,
    WalletWithdrawSerializer,
)
from apps.orders.services import BillingService, DeliveryGateway, OrderService, PaymentService, create_order, \
    wallet_withdraw
from apps.orders.services.payment import PaymentInitiationResult
from apps.orders.services.wallet import WalletInsufficientFunds, get_wallet_balance
from apps.users.models import Profile


class IdempotencyMixin:
    idempotency_header = "HTTP_IDEMPOTENCY_KEY"

    def require_idempotency_key(self) -> str:
        key = self.request.META.get(self.idempotency_header)
        if not key:
            raise serializers.ValidationError({"detail": "Idempotency-Key header is required"})
        return key


class WalletProfileMixin:
    """Common helper to guarantee that the authenticated user has a profile."""

    _profile_cache_attr = "_wallet_profile"

    def get_profile(self):
        profile = getattr(self, self._profile_cache_attr, None)
        if profile is not None:
            return profile
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        setattr(self, self._profile_cache_attr, profile)
        return profile


class WalletTransactionViewSet(
    WalletProfileMixin,
    IdempotencyMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = self.get_profile()
        queryset = WalletTransaction.objects.filter(profile=profile)
        currency = self.request.query_params.get("currency")
        if currency in dict(WalletTransaction.Currency.choices):
            queryset = queryset.filter(currency=currency)
        return queryset.order_by("-created_at", "-id")

    def get_serializer_class(self):
        if self.action == "topup":
            return WalletTopUpSerializer
        if self.action == "withdraw":
            return WalletWithdrawSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["profile"] = self.get_profile()
        if self.request.method in ("POST", "PUT", "PATCH"):
            try:
                context["idempotency_key"] = self.require_idempotency_key()
            except serializers.ValidationError:
                context["idempotency_key"] = None
        return context

    @action(detail=False, methods=["post"])
    def topup(self, request, *args, **kwargs):
        self.require_idempotency_key()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_record = serializer.create_transaction(profile=self.get_profile())
        output = WalletTransactionSerializer(transaction_record, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def withdraw(self, request, *args, **kwargs):
        self.require_idempotency_key()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_record = serializer.create_transaction(profile=self.get_profile())
        output = WalletTransactionSerializer(transaction_record, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class OrderViewSet(
    WalletProfileMixin,
    IdempotencyMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(profile=self.get_profile())
            .select_related("payment_transaction")
            .order_by("-created_at", "-id")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["profile"] = self.get_profile()
        context["idempotency_key"] = self.require_idempotency_key() if self.request.method == "POST" else None
        return context

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, *args, **kwargs):
        self.require_idempotency_key()
        order = self.get_object()
        serializer = OrderPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save(order)
        output = self.get_serializer(updated)
        return Response(output.data)


class WalletSummaryView(WalletProfileMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profile = self.get_profile()
        profile.refresh_from_db()
        payload = WalletSummarySerializer.for_profile(profile)
        serializer = WalletSummarySerializer(payload)
        return Response(serializer.data)


class WalletBalancesView(WalletProfileMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profile = self.get_profile()
        balances = {}
        for currency, _ in WalletTransaction.Currency.choices:
            balance = get_wallet_balance(profile, currency)
            balances[currency.lower()] = {
                "total": float(balance.total) if currency != WalletTransaction.Currency.TELEGRAM_STARS else int(balance.total),
                "available": float(balance.available)
                if currency != WalletTransaction.Currency.TELEGRAM_STARS
                else int(balance.available),
            }
        return Response({"balances": balances})


class WalletTopUpView(WalletProfileMixin, IdempotencyMixin, APIView):
    permission_classes = [IsAuthenticated]
    payment_service = PaymentService()

    class Serializer(serializers.Serializer):
        currency = serializers.ChoiceField(choices=WalletTransaction.Currency.choices)
        amount = serializers.DecimalField(max_digits=12, decimal_places=2)
        provider = serializers.ChoiceField(choices=PaymentAttempt.Provider.choices)
        metadata = serializers.JSONField(required=False)

    def post(self, request, *args, **kwargs):
        key = self.require_idempotency_key()
        serializer = self.Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.get_profile()
        amount = Decimal(serializer.validated_data["amount"])
        result: PaymentInitiationResult = self.payment_service.start_wallet_topup(
            profile,
            currency=serializer.validated_data["currency"],
            amount=amount,
            provider=serializer.validated_data["provider"],
            idempotency_key=key,
            metadata=serializer.validated_data.get("metadata"),
        )
        payload = {
            "payment_attempt_id": result.payment_attempt.pk,
            "provider": result.payment_attempt.provider,
            "status": result.payment_attempt.status,
            "confirmation": result.confirmation_data,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class WalletManualStarsTopUpView(WalletProfileMixin, IdempotencyMixin, APIView):
    permission_classes = [IsAuthenticated]
    payment_service = PaymentService()

    class Serializer(serializers.Serializer):
        amount = serializers.IntegerField(min_value=1)
        source = serializers.CharField(max_length=64, default="crm_purchase_card")
        metadata = serializers.JSONField(required=False)

    def post(self, request, *args, **kwargs):
        key = self.require_idempotency_key()
        serializer = self.Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.get_profile()
        tx = self.payment_service.manual_credit(
            profile,
            currency=WalletTransaction.Currency.TELEGRAM_STARS,
            amount=Decimal(serializer.validated_data["amount"]),
            source=serializer.validated_data["source"],
            idempotency_key=key,
            metadata=serializer.validated_data.get("metadata"),
        )
        return Response(WalletTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class CheckoutItemSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=6, decimal_places=2, default=Decimal("1.00"))
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CheckoutRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    kind = serializers.CharField(required=False, allow_blank=True)
    currency = serializers.ChoiceField(choices=Order.Currency.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_service = serializers.PrimaryKeyRelatedField(queryset=DeliveryService.objects.all())
    delivery_window = serializers.PrimaryKeyRelatedField(queryset=DeliveryWindow.objects.all(), required=False)
    delivery_date = serializers.DateField(required=False)
    address = serializers.CharField(max_length=255)
    metadata = serializers.JSONField(required=False)
    items = CheckoutItemSerializer(many=True)


class CheckoutView(WalletProfileMixin, IdempotencyMixin, APIView):
    permission_classes = [IsAuthenticated]
    payment_service = PaymentService()

    def post(self, request, *args, **kwargs):
        idempotency_key = self.require_idempotency_key()
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.get_profile()
        data = serializer.validated_data
        order = create_order(
            profile,
            title=data["title"],
            currency=data["currency"],
            amount=data["amount"],
            description=data.get("description"),
            kind=data.get("kind") or Order.Kind.OTHER,
            metadata=data.get("metadata") or {},
        )
        order.delivery_service = data["delivery_service"]
        order.delivery_window = data.get("delivery_window")
        order.delivery_date = data.get("delivery_date")
        order.address_line = data["address"]
        order.items_count = len(data["items"])
        order.save(update_fields=[
            "delivery_service",
            "delivery_window",
            "delivery_date",
            "address_line",
            "items_count",
            "updated_at",
        ])
        gateway = DeliveryGateway(order.delivery_service)
        gateway.create_delivery(order, idempotency_key=idempotency_key)
        provider = (
            PaymentAttempt.Provider.CALOCOIN
            if order.currency == Order.Currency.CALCOCOIN
            else PaymentAttempt.Provider.TELEGRAM_STARS
        )
        attempt = self.payment_service.start_order_payment(
            order,
            currency=order.currency,
            amount=order.total_price,
            provider=provider,
            idempotency_key=f"{idempotency_key}:{provider}",
            metadata={"source": "checkout"},
        )
        if provider == PaymentAttempt.Provider.CALOCOIN:
            self.payment_service.complete_calocoin_payment(
                attempt,
                idempotency_key=f"{idempotency_key}:capture",
            )
            OrderService(order).confirm()
        payload = {
            "order_id": order.pk,
            "status": order.status,
            "payment_attempt_id": attempt.pk,
            "provider": attempt.provider,
            "payment_status": attempt.status,
            "confirmation": attempt.confirmation_payload,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class SubscriptionAutopayToggleView(WalletProfileMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, subscription_id: int, action: str, *args, **kwargs):
        subscription = get_object_or_404(MealSubscription, pk=subscription_id, user=request.user)
        if action == "enable":
            subscription.autopay_enabled = True
        elif action == "disable":
            subscription.autopay_enabled = False
        else:
            raise serializers.ValidationError({"detail": "Unknown action"})
        subscription.save(update_fields=["autopay_enabled", "updated_at"])
        return Response({"autopay_enabled": subscription.autopay_enabled})


class SubscriptionChargeView(WalletProfileMixin, IdempotencyMixin, APIView):
    permission_classes = [IsAuthenticated]
    billing_service = BillingService()

    def post(self, request, subscription_id: int, *args, **kwargs):
        subscription = get_object_or_404(MealSubscription, pk=subscription_id, user=request.user)
        key = self.require_idempotency_key()
        result = self.billing_service.charge_subscription(subscription, idempotency_key=key)
        return Response(
            {
                "subscription_id": subscription.pk,
                "success": result.success,
                "message": result.message,
                "order_id": result.order.pk if result.order else None,
                "payment_attempt_id": result.payment_attempt.pk if result.payment_attempt else None,
            }
        )


class ComposeRecipePurchaseView(WalletProfileMixin, IdempotencyMixin, APIView):
    permission_classes = [IsAuthenticated]

    class Serializer(serializers.Serializer):
        currency = serializers.ChoiceField(choices=WalletTransaction.Currency.choices)
        amount = serializers.DecimalField(max_digits=10, decimal_places=2)
        metadata = serializers.JSONField(required=False)

    def post(self, request, *args, **kwargs):
        key = self.require_idempotency_key()
        serializer = self.Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.get_profile()
        try:
            tx = wallet_withdraw(
                profile,
                currency=serializer.validated_data["currency"],
                amount=serializer.validated_data["amount"],
                description="Покупка функции compose_recipe",
                metadata={"feature": "compose_recipe", **(serializer.validated_data.get("metadata") or {})},
                idempotency_key=key,
            )
        except WalletInsufficientFunds as exc:
            raise serializers.ValidationError({"amount": str(exc)}) from exc
        return Response(WalletTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class TelegramStarsWebhookView(IdempotencyMixin, APIView):
    permission_classes = [AllowAny]
    payment_service = PaymentService()

    def post(self, request, *args, **kwargs):
        key = self.require_idempotency_key()
        event = self.payment_service.handle_webhook(
            PaymentAttempt.Provider.TELEGRAM_STARS,
            request.data,
            idempotency_key=key,
        )
        status_code = status.HTTP_200_OK if event.status != IntegrationWebhookEvent.ProcessingStatus.FAILED else status.HTTP_400_BAD_REQUEST
        return Response({"status": event.status, "event_id": event.pk}, status=status_code)


class CardWebhookView(IdempotencyMixin, APIView):
    permission_classes = [AllowAny]
    payment_service = PaymentService()

    def post(self, request, *args, **kwargs):
        key = self.require_idempotency_key()
        event = self.payment_service.handle_webhook(
            PaymentAttempt.Provider.CARD,
            request.data,
            idempotency_key=key,
        )
        status_code = status.HTTP_200_OK if event.status != IntegrationWebhookEvent.ProcessingStatus.FAILED else status.HTTP_400_BAD_REQUEST
        return Response({"status": event.status, "event_id": event.pk}, status=status_code)


__all__ = [
    "WalletTransactionViewSet",
    "OrderViewSet",
    "WalletSummaryView",
    "WalletBalancesView",
    "WalletTopUpView",
    "WalletManualStarsTopUpView",
    "CheckoutView",
    "SubscriptionAutopayToggleView",
    "SubscriptionChargeView",
    "ComposeRecipePurchaseView",
    "TelegramStarsWebhookView",
    "CardWebhookView",
]
