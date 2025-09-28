from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import uuid

from django.utils import timezone

from ..models import DeliveryService, Order


@dataclass
class DeliveryResult:
    order: Order
    external_id: str
    tracking_url: Optional[str]
    payload: Dict[str, str]


class DeliveryGateway:
    """Simple integration facade for delivery partners."""

    def __init__(self, service: DeliveryService) -> None:
        self.service = service

    def create_delivery(
        self,
        order: Order,
        *,
        idempotency_key: str | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> DeliveryResult:
        if order.external_order_id:
            return DeliveryResult(order, order.external_order_id, order.tracking_url, order.metadata.get("delivery", {}))
        external_id = f"{self.service.slug}-{uuid.uuid4().hex[:12]}"
        tracking_url = None
        if self.service.supports_live_tracking:
            tracking_url = f"https://tracking.{self.service.slug}.ru/{external_id}"
        payload = {
            "idempotency_key": idempotency_key or uuid.uuid4().hex,
            "service": self.service.slug,
            "created_at": timezone.now().isoformat(),
        }
        if metadata:
            payload.update(metadata)
        Order.objects.filter(pk=order.pk).update(
            external_order_id=external_id,
            tracking_url=tracking_url or "",
            metadata={**order.metadata, "delivery": payload},
            updated_at=timezone.now(),
        )
        order.refresh_from_db()
        return DeliveryResult(order, external_id, tracking_url, payload)

    def cancel_delivery(self, order: Order, *, reason: str | None = None) -> DeliveryResult:
        payload = order.metadata.get("delivery", {}).copy()
        payload.update({
            "cancelled_at": timezone.now().isoformat(),
            "cancel_reason": reason or "",
        })
        Order.objects.filter(pk=order.pk).update(
            metadata={**order.metadata, "delivery": payload},
            updated_at=timezone.now(),
        )
        order.refresh_from_db()
        return DeliveryResult(order, order.external_order_id or "", order.tracking_url, payload)

    def refresh_tracking(self, order: Order) -> DeliveryResult:
        payload = order.metadata.get("delivery", {}).copy()
        payload["last_checked_at"] = timezone.now().isoformat()
        if self.service.supports_live_tracking and order.external_order_id:
            tracking_url = f"https://tracking.{self.service.slug}.ru/{order.external_order_id}?t={int(timezone.now().timestamp())}"
        else:
            tracking_url = order.tracking_url
        Order.objects.filter(pk=order.pk).update(
            metadata={**order.metadata, "delivery": payload},
            tracking_url=tracking_url or "",
            updated_at=timezone.now(),
        )
        order.refresh_from_db()
        return DeliveryResult(order, order.external_order_id or "", tracking_url, payload)


__all__ = ["DeliveryGateway", "DeliveryResult"]