from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task
from django.utils import timezone

from apps.orders.models import MealSubscription, Order, PaymentAttempt
from apps.orders.services import BillingService, DeliveryGateway, OrderService, PaymentService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def process_payment_attempt(self, payment_attempt_id: int, *, idempotency_key: str | None = None) -> Dict[str, Any]:
    payment_service = PaymentService()
    attempt = PaymentAttempt.objects.select_related("order").get(pk=payment_attempt_id)
    logger.info("Processing payment attempt %s via Celery", payment_attempt_id)
    if attempt.provider == PaymentAttempt.Provider.CALOCOIN:
        payment_service.complete_calocoin_payment(attempt, idempotency_key=idempotency_key)
        if attempt.order_id:
            OrderService(attempt.order).confirm()
    else:
        logger.info("Payment attempt %s handled asynchronously by webhook", payment_attempt_id)
    return {
        "payment_attempt_id": attempt.pk,
        "status": attempt.status,
    }


@shared_task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def trigger_subscription_autopay(self, subscription_id: int, *, idempotency_key: str) -> Dict[str, Any]:
    billing_service = BillingService()
    subscription = MealSubscription.objects.get(pk=subscription_id)
    result = billing_service.charge_subscription(subscription, idempotency_key=idempotency_key)
    logger.info(
        "Subscription %s autopay processed: success=%s", subscription_id, result.success
    )
    return {
        "subscription_id": subscription_id,
        "success": result.success,
        "message": result.message,
    }


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def sync_delivery_status(self, order_id: int) -> Dict[str, Any]:
    order = Order.objects.select_related("delivery_service").get(pk=order_id)
    if not order.delivery_service:
        logger.warning("Order %s has no delivery service to sync", order_id)
        return {"order_id": order_id, "status": order.status}
    gateway = DeliveryGateway(order.delivery_service)
    result = gateway.refresh_tracking(order)
    logger.info("Delivery status synced for order %s", order_id)
    return {
        "order_id": order_id,
        "status": result.order.status,
        "tracking_url": result.tracking_url,
    }


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def send_payment_notification(self, order_id: int, *, success: bool) -> Dict[str, Any]:
    order = Order.objects.get(pk=order_id)
    payload = {
        "order_id": order_id,
        "status": order.status,
        "success": success,
        "wallet_currency": order.wallet_currency,
        "notified_at": timezone.now().isoformat(),
    }
    logger.info("Would send notification: %s", payload)
    return payload


__all__ = [
    "process_payment_attempt",
    "trigger_subscription_autopay",
    "sync_delivery_status",
    "send_payment_notification",
]