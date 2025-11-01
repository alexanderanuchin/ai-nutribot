from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Cart, CartItem, Product
from nutribot.middleware import get_request_id

logger = logging.getLogger(__name__)


class CartSubmissionSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=0, required=False, default=1)


class CartSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    serializer_class = CartSubmissionSerializer

    def post(self, request, *args, **kwargs):  # noqa: D401 - DRF signature
        """Add, update or remove cart items using a simple payload."""

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            product = (
                Product.objects.select_related("store")
                .get(pk=payload["product_id"], is_published=True, store__is_active=True)
            )
        except Product.DoesNotExist as exc:  # pragma: no cover - handled below
            raise serializers.ValidationError({"product_id": "Товар не найден или недоступен"}) from exc

        rid = getattr(request, "request_id", get_request_id())
        quantity: int = payload["quantity"]

        with transaction.atomic():
            cart, _created = Cart.objects.select_for_update().get_or_create(
                user=request.user,
                store=product.store,
                status=Cart.Status.ACTIVE,
                defaults={"currency": product.currency or "RUB"},
            )

            update_fields: list[str] = ["updated_at"]
            if product.currency and cart.currency != product.currency:
                cart.currency = product.currency
                update_fields.append("currency")
            cart.save(update_fields=update_fields)

            item_payload: dict | None = None
            status_code = status.HTTP_200_OK

            if quantity <= 0:
                deleted, _ = CartItem.objects.filter(cart=cart, product=product).delete()
                action = "removed" if deleted else "noop"
            else:
                cart_item, created = CartItem.objects.select_for_update().get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        "quantity": quantity,
                        "price_snapshot": product.price,
                    },
                )
                if not created:
                    has_changes = False
                    if cart_item.quantity != quantity:
                        cart_item.quantity = quantity
                        has_changes = True
                    if cart_item.price_snapshot != product.price:
                        cart_item.price_snapshot = Decimal(product.price)
                        has_changes = True
                    if has_changes:
                        cart_item.save(update_fields=["quantity", "price_snapshot"])
                    action = "updated"
                else:
                    action = "created"
                    status_code = status.HTTP_201_CREATED

                item_payload = {
                    "id": cart_item.id,
                    "product_id": cart_item.product_id,
                    "quantity": cart_item.quantity,
                    "price_snapshot": str(cart_item.price_snapshot),
                }

            aggregates = cart.items.aggregate(
                items_count=Count("id"),
                items_quantity=Sum("quantity"),
            )
            items_count = int(aggregates.get("items_count") or 0)
            items_quantity = int(aggregates.get("items_quantity") or 0)

        logger.info(
            "market.cart.submit",
            extra={
                "rid": rid,
                "user_id": request.user.id,
                "product_id": product.id,
                "quantity": quantity,
                "action": action,
            },
        )

        response_data = {
            "status": "removed" if action == "noop" else action,
            "cart": {
                "id": cart.id,
                "store_id": cart.store_id,
                "currency": cart.currency,
                "items_count": items_count,
                "items_quantity": items_quantity,
            },
            "item": item_payload,
        }
        return Response(response_data, status=status_code)
