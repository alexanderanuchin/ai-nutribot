from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Optional

from django.db import transaction
from django.utils import timezone

from ..models import IntegrationWebhookEvent, Order, PaymentAttempt, WalletTransaction


class OrderStatusTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


@dataclass
class PaymentResult:
    success: bool
    wallet_transaction: Optional[WalletTransaction] = None
    wallet_currency: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None


class OrderService:
    """Encapsulates allowed transitions and payment application logic."""

    _ALLOWED_TRANSITIONS: Mapping[str, Iterable[str]] = {
        Order.Status.DRAFT: {Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED},
        Order.Status.PENDING_PAYMENT: {
            Order.Status.PAID,
            Order.Status.PAYMENT_FAILED,
            Order.Status.CANCELLED,
        },
        Order.Status.PAYMENT_FAILED: {Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED},
        Order.Status.PAID: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
        Order.Status.CONFIRMED: {Order.Status.PREPARING, Order.Status.CANCELLED},
        Order.Status.PREPARING: {Order.Status.OUT_FOR_DELIVERY, Order.Status.CANCELLED},
        Order.Status.OUT_FOR_DELIVERY: {Order.Status.DELIVERED, Order.Status.CANCELLED},
        Order.Status.DELIVERED: set(),
        Order.Status.CANCELLED: set(),
    }

    TERMINAL_STATUSES = {Order.Status.CANCELLED, Order.Status.DELIVERED}

    def __init__(self, order: Order):
        self.order = order

    def refresh(self) -> Order:
        self.order.refresh_from_db()
        return self.order

    def _transition(self, new_status: str) -> Order:
        current = self.order.status
        if current == new_status:
            return self.order
        allowed = set(self._ALLOWED_TRANSITIONS.get(current, set()))
        if new_status not in allowed:
            raise OrderStatusTransitionError(
                f"Transition from {current} to {new_status} is not permitted"
            )
        updates: MutableMapping[str, object] = {
            "status": new_status,
            "updated_at": timezone.now(),
        }
        if new_status == Order.Status.CANCELLED:
            updates["cancelled_at"] = timezone.now()
        if new_status == Order.Status.PAID and not self.order.paid_at:
            updates["paid_at"] = timezone.now()
        Order.objects.filter(pk=self.order.pk).update(**updates)
        self.order.refresh_from_db()
        return self.order

    def mark_payment_initiated(self) -> Order:
        return self._transition(Order.Status.PENDING_PAYMENT)

    def mark_payment_failed(self, *, reason: str | None = None) -> Order:
        order = self._transition(Order.Status.PAYMENT_FAILED)
        if reason:
            Order.objects.filter(pk=order.pk).update(
                cancellation_reason=reason,
                updated_at=timezone.now(),
            )
            order.refresh_from_db()
        return order

    def mark_paid(self, *, wallet_currency: str | None = None) -> Order:
        order = self._transition(Order.Status.PAID)
        if wallet_currency:
            Order.objects.filter(pk=order.pk).update(wallet_currency=wallet_currency)
            order.wallet_currency = wallet_currency
        return order

    def confirm(self) -> Order:
        return self._transition(Order.Status.CONFIRMED)

    def start_preparing(self) -> Order:
        return self._transition(Order.Status.PREPARING)

    def mark_out_for_delivery(self) -> Order:
        return self._transition(Order.Status.OUT_FOR_DELIVERY)

    def mark_delivered(self) -> Order:
        return self._transition(Order.Status.DELIVERED)

    def cancel(self, *, reason: str | None = None) -> Order:
        order = self._transition(Order.Status.CANCELLED)
        if reason:
            Order.objects.filter(pk=order.pk).update(
                cancellation_reason=reason,
                updated_at=timezone.now(),
            )
            order.refresh_from_db()
        return order

    def apply_payment_result(
        self,
        payment_attempt: PaymentAttempt,
        result: PaymentResult,
        *,
        webhook_event: IntegrationWebhookEvent | None = None,
    ) -> Order:
        """Apply payment outcome and transition the order accordingly."""

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.order.pk)
            attempt = PaymentAttempt.objects.select_for_update().get(pk=payment_attempt.pk)
            if attempt.status in {PaymentAttempt.Status.SUCCEEDED, PaymentAttempt.Status.CANCELLED}:
                self.order = order
                return order

            timestamp = timezone.now()
            if result.success:
                attempt.status = PaymentAttempt.Status.SUCCEEDED
                attempt.processed_at = timestamp
                if result.wallet_transaction and not order.payment_transaction_id:
                    order.payment_transaction = result.wallet_transaction
                if result.wallet_currency:
                    order.wallet_currency = result.wallet_currency
                order.status = Order.Status.PAID
                order.paid_at = order.paid_at or timestamp
                order.updated_at = timestamp
                order.save(update_fields=[
                    "status",
                    "wallet_currency",
                    "payment_transaction",
                    "paid_at",
                    "updated_at",
                ])
            else:
                attempt.status = PaymentAttempt.Status.FAILED
                attempt.failure_code = result.failure_code or attempt.failure_code
                attempt.failure_reason = result.failure_reason or attempt.failure_reason
                attempt.processed_at = timestamp
                order.status = Order.Status.PAYMENT_FAILED
                if result.failure_reason:
                    order.cancellation_reason = result.failure_reason
                order.updated_at = timestamp
                order.save(update_fields=["status", "cancellation_reason", "updated_at"])

            attempt.updated_at = timestamp
            attempt.save(update_fields=[
                "status",
                "failure_code",
                "failure_reason",
                "processed_at",
                "updated_at",
            ])

            if webhook_event:
                IntegrationWebhookEvent.objects.filter(pk=webhook_event.pk).update(
                    status=IntegrationWebhookEvent.ProcessingStatus.PROCESSED,
                    processed_at=timestamp,
                )

            self.order = order
            return order


__all__ = ["OrderService", "OrderStatusTransitionError", "PaymentResult"]