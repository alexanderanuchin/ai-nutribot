from __future__ import annotations

# Create your views here.
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, WalletTransaction
from apps.users.models import Profile
from apps.orders.serializers import (
    OrderPaymentSerializer,
    OrderSerializer,
    WalletSummarySerializer,
    WalletTopUpSerializer,
    WalletTransactionSerializer,
    WalletWithdrawSerializer,
)


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


class WalletTransactionViewSet(WalletProfileMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
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
        return context

    @action(detail=False, methods=["post"])
    def topup(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_record = serializer.create_transaction(profile=self.get_profile())
        output = WalletTransactionSerializer(transaction_record, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def withdraw(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_record = serializer.create_transaction(profile=self.get_profile())
        output = WalletTransactionSerializer(transaction_record, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class OrderViewSet(WalletProfileMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
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
        return context

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, *args, **kwargs):
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


__all__ = [
    "WalletTransactionViewSet",
    "OrderViewSet",
    "WalletSummaryView",
]