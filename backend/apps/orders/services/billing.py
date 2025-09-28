from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Tuple

from django.db import transaction
from django.utils import timezone

from ..models import MealSubscription, Order, PaymentAttempt, SubscriptionPlan, WalletTransaction
from .order import OrderService, PaymentResult
from .payment import PaymentService
from .wallet import WalletInsufficientFunds, wallet_withdraw


@dataclass
class BillingResult:
    subscription: MealSubscription
    order: Order
    payment_attempt: PaymentAttempt | None
    success: bool
    message: str


class BillingService:
    """Responsible for subscription billing cycles and autopay charges."""

    PERIOD_DAYS: Dict[str, int] = {
        SubscriptionPlan.BillingPeriod.WEEKLY: 7,
        SubscriptionPlan.BillingPeriod.MONTHLY: 30,
        SubscriptionPlan.BillingPeriod.QUARTERLY: 90,
    }

    def __init__(self, payment_service: PaymentService | None = None) -> None:
        self.payment_service = payment_service or PaymentService()

    def _compute_next_period(self, subscription: MealSubscription) -> Tuple[date, date]:
        today = timezone.now().date()
        if subscription.current_period_end:
            start = subscription.current_period_end + timedelta(days=1)
        else:
            start = subscription.current_period_start or today
        period_days = self.PERIOD_DAYS.get(subscription.plan.billing_period, 7)
        end = start + timedelta(days=period_days - 1)
        return start, end

    def _ensure_order(self, subscription: MealSubscription, *, reference: str, amount: Decimal, currency: str) -> Order:
        order, created = Order.objects.get_or_create(
            subscription=subscription,
            reference=reference,
            defaults={
                "user": subscription.user,
                "profile": subscription.profile,
                "title": f"Подписка {subscription.plan.name}",
                "description": "Автосписание подписки",
                "kind": Order.Kind.PRO_SUBSCRIPTION,
                "currency": currency,
                "total_price": amount,
                "status": Order.Status.PENDING_PAYMENT,
            },
        )
        if not created and order.total_price != amount:
            order.total_price = amount
            order.currency = currency
            order.save(update_fields=["total_price", "currency", "updated_at"])
        return order

    def _attempt_wallet_payment(
        self,
        subscription: MealSubscription,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        provider: str,
        idempotency_key: str,
    ) -> PaymentAttempt:
        attempt = PaymentAttempt.objects.create(
            order=order,
            subscription=subscription,
            provider=provider,
            status=PaymentAttempt.Status.INITIATED,
            amount=amount,
            currency=currency,
            external_payment_id=f"sub-{subscription.pk}-{timezone.now().timestamp()}",
            confirmation_payload={"subscription_id": subscription.pk},
        )
        try:
            tx = wallet_withdraw(
                subscription.profile,
                currency=currency,
                amount=amount,
                description=f"Автосписание подписки #{subscription.pk}",
                metadata={"subscription_id": subscription.pk, "payment_attempt_id": attempt.pk},
                related_order=order,
                idempotency_key=idempotency_key,
            )
        except WalletInsufficientFunds:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.failure_reason = "Недостаточно средств"
            attempt.processed_at = timezone.now()
            attempt.save(update_fields=["status", "failure_reason", "processed_at", "updated_at"])
            OrderService(order).mark_payment_failed(reason="Недостаточно средств")
            return attempt

        attempt.status = PaymentAttempt.Status.SUCCEEDED
        attempt.wallet_transaction = tx
        attempt.processed_at = timezone.now()
        attempt.save(update_fields=["status", "wallet_transaction", "processed_at", "updated_at"])
        OrderService(order).apply_payment_result(
            attempt,
            PaymentResult(
                success=True,
                wallet_transaction=tx,
                wallet_currency=currency,
            ),
        )
        return attempt

    def charge_subscription(
        self,
        subscription: MealSubscription,
        *,
        idempotency_key: str,
    ) -> BillingResult:
        if not subscription.autopay_enabled:
            return BillingResult(subscription, None, None, False, "Autopay disabled")
        amount_calo = subscription.plan.price_calocoin
        amount_stars = subscription.plan.price_telegram_stars
        if not amount_calo and not amount_stars:
            return BillingResult(subscription, None, None, False, "No pricing configured")

        period_start, period_end = self._compute_next_period(subscription)
        reference = f"sub-{subscription.pk}-{period_start.isoformat()}"
        currency = WalletTransaction.Currency.CALOCOIN if amount_calo else WalletTransaction.Currency.TELEGRAM_STARS
        amount = Decimal(amount_calo or amount_stars or 0)
        order = self._ensure_order(subscription, reference=reference, amount=amount, currency=currency)

        attempt: PaymentAttempt | None = None
        success = False
        message = ""
        with transaction.atomic():
            subscription = MealSubscription.objects.select_for_update().get(pk=subscription.pk)
            order = Order.objects.select_for_update().get(pk=order.pk)
            if amount_calo:
                attempt = self._attempt_wallet_payment(
                    subscription,
                    order,
                    currency=WalletTransaction.Currency.CALOCOIN,
                    amount=Decimal(amount_calo),
                    provider=PaymentAttempt.Provider.CALOCOIN,
                    idempotency_key=f"{idempotency_key}:calo",
                )
                success = attempt.status == PaymentAttempt.Status.SUCCEEDED
                message = attempt.failure_reason or ""
            if not success and amount_stars:
                attempt = self._attempt_wallet_payment(
                    subscription,
                    order,
                    currency=WalletTransaction.Currency.TELEGRAM_STARS,
                    amount=Decimal(amount_stars),
                    provider=PaymentAttempt.Provider.TELEGRAM_STARS,
                    idempotency_key=f"{idempotency_key}:stars",
                )
                success = attempt.status == PaymentAttempt.Status.SUCCEEDED
                message = attempt.failure_reason or ""

            if success:
                subscription.status = MealSubscription.Status.ACTIVE
                subscription.current_period_start = period_start
                subscription.current_period_end = period_end
                next_billing = period_end + timedelta(days=1)
                subscription.next_billing_at = timezone.make_aware(
                    datetime.combine(next_billing, datetime.min.time())
                )
                subscription.save(update_fields=[
                    "status",
                    "current_period_start",
                    "current_period_end",
                    "next_billing_at",
                    "updated_at",
                ])
                message = "Autopay succeeded"
            else:
                subscription.status = MealSubscription.Status.PAUSED
                subscription.next_billing_at = timezone.now() + timedelta(days=1)
                subscription.save(update_fields=["status", "next_billing_at", "updated_at"])
                message = message or "Autopay failed"

        return BillingResult(subscription, order, attempt, success, message)


__all__ = ["BillingService", "BillingResult"]