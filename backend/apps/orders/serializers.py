from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from rest_framework import serializers

from apps.orders.models import Order, WalletTransaction
from apps.orders.services import (
    build_wallet_summary,
    create_order,
    normalize_transaction_direction,
    pay_order_from_wallet,
    wallet_topup,
    wallet_withdraw,
)


class WalletTransactionSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    balance_before = serializers.SerializerMethodField()
    balance_after = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = (
            "id",
            "currency",
            "direction",
            "amount",
            "balance_before",
            "balance_after",
            "description",
            "reference",
            "metadata",
            "created_at",
        )
        read_only_fields = fields

    @staticmethod
    def _format(value: Decimal, currency: str) -> float | int:
        if currency == WalletTransaction.Currency.TELEGRAM_STARS:
            return int(value)
        return float(value)

    def get_amount(self, obj: WalletTransaction) -> float | int:
        return self._format(obj.amount, obj.currency)

    def get_balance_before(self, obj: WalletTransaction) -> float | int:
        return self._format(obj.balance_before, obj.currency)

    def get_balance_after(self, obj: WalletTransaction) -> float | int:
        return self._format(obj.balance_after, obj.currency)

    def to_representation(self, instance: WalletTransaction) -> Dict[str, Any]:
        data = super().to_representation(instance)
        data["currency"] = instance.currency.lower()
        data["direction"] = normalize_transaction_direction(instance.direction)
        data["reference"] = data.get("reference") or None
        return data


class WalletOperationSerializer(serializers.Serializer):
    currency = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=64)
    metadata = serializers.JSONField(required=False)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть положительной")
        return value

    def validate_currency(self, value: str) -> str:
        normalized = value.upper()
        valid = {choice for choice, _ in WalletTransaction.Currency.choices}
        if normalized not in valid:
            raise serializers.ValidationError("Неизвестная валюта")
        return normalized

    def create_transaction(self, *, profile) -> WalletTransaction:
        raise NotImplementedError


class WalletTopUpSerializer(WalletOperationSerializer):
    def create_transaction(self, *, profile) -> WalletTransaction:
        return wallet_topup(
            profile,
            currency=self.validated_data["currency"],
            amount=self.validated_data["amount"],
            description=self.validated_data.get("description"),
            reference=self.validated_data.get("reference"),
            metadata=self.validated_data.get("metadata"),
        )


class WalletWithdrawSerializer(WalletOperationSerializer):
    def create_transaction(self, *, profile) -> WalletTransaction:
        try:
            return wallet_withdraw(
                profile,
                currency=self.validated_data["currency"],
                amount=self.validated_data["amount"],
                description=self.validated_data.get("description"),
                reference=self.validated_data.get("reference"),
                metadata=self.validated_data.get("metadata"),
            )
        except ValueError as exc:
            raise serializers.ValidationError({"amount": str(exc)}) from exc


class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    currency = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pay_with_wallet = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Order
        fields = (
            "id",
            "title",
            "description",
            "kind",
            "status",
            "status_display",
            "currency",
            "amount",
            "reference",
            "metadata",
            "pay_with_wallet",
            "paid_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "status_display",
            "paid_at",
            "created_at",
        )

    def create(self, validated_data: Dict[str, Any]) -> Order:
        pay_with_wallet = validated_data.pop("pay_with_wallet", False)
        profile = self.context["profile"]
        currency = validated_data.get("currency")
        if isinstance(currency, str):
            validated_data["currency"] = currency.upper()
        order = create_order(profile, **validated_data)
        if pay_with_wallet:
            try:
                order, _ = pay_order_from_wallet(order)
            except ValueError as exc:
                raise serializers.ValidationError({"pay_with_wallet": str(exc)}) from exc
        return order

    def to_representation(self, instance: Order) -> Dict[str, Any]:
        data = super().to_representation(instance)
        amount = instance.total_price
        if instance.currency == WalletTransaction.Currency.TELEGRAM_STARS:
            data["amount"] = int(amount)
        else:
            data["amount"] = float(amount)
        data["currency"] = instance.currency.lower()
        return data

    def validate_currency(self, value: str) -> str:
        normalized = value.upper()
        valid = {choice for choice, _ in WalletTransaction.Currency.choices}
        if normalized not in valid:
            raise serializers.ValidationError("Неизвестная валюта")
        return normalized


class OrderPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(required=False, allow_blank=True, max_length=64)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    metadata = serializers.JSONField(required=False)

    def save(self, order: Order) -> Order:
        try:
            updated, _ = pay_order_from_wallet(
                order,
                description=self.validated_data.get("description"),
                reference=self.validated_data.get("reference"),
                metadata=self.validated_data.get("metadata"),
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return updated


class WalletSummarySerializer(serializers.Serializer):
    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return instance

    @classmethod
    def for_profile(cls, profile):
        return build_wallet_summary(profile)


__all__ = [
    "WalletTransactionSerializer",
    "WalletTopUpSerializer",
    "WalletWithdrawSerializer",
    "OrderSerializer",
    "OrderPaymentSerializer",
    "WalletSummarySerializer",
]