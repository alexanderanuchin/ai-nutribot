from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Iterable, Mapping

from django.db import transaction
from django.db.models import F, Prefetch

from apps.market.events import publish_market_event, serialize_instance
from apps.market.models import Cart, CartItem, Inventory, Product
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.orders.services import create_order, pay_order_from_wallet
from apps.orders.services.wallet import WalletInsufficientFunds
from apps.users.models import Profile
from nutribot.middleware import get_request_id

logger = logging.getLogger("audit.market.checkout")


class CartCheckoutError(Exception):
    """Base exception for checkout failures."""


class CartInactiveError(CartCheckoutError):
    """Raised when attempting to checkout a non-active cart."""


class CartEmptyError(CartCheckoutError):
    """Raised when attempting to checkout an empty cart."""


class InventoryInsufficientError(CartCheckoutError):
    """Raised when inventory cannot fulfil the requested quantity."""

    def __init__(self, *, product_id: int, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            "Недостаточно товара на складе",
        )


@dataclass(slots=True)
class CartCheckoutResult:
    order: Order
    cart: Cart
    was_paid: bool


def _ensure_currency(code: str | None, fallback: str) -> str:
    currency = (code or fallback or Order.Currency.RUB).upper()
    valid = {choice for choice, _ in Order.Currency.choices}
    if currency not in valid:
        raise ValueError(f"Unsupported currency: {currency}")
    return currency


def _build_order_description(titles: Iterable[str], total_quantity: int) -> str:
    items = [title for title in titles if title]
    if not items:
        base = "Товары" if total_quantity else "Корзина"
        return f"{base}: всего {total_quantity} шт."[:255]
    if len(items) > 3:
        head = ", ".join(items[:3])
        summary = f"{head} и ещё {len(items) - 3}"
    else:
        summary = ", ".join(items)
    description = f"Товары: {summary} (всего {total_quantity} шт.)"
    return description[:255]


def _serialize_items(items: Iterable[CartItem]) -> list[Mapping[str, object]]:
    payload: list[Mapping[str, object]] = []
    for item in items:
        payload.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_title": getattr(item.product, "title", ""),
                "quantity": item.quantity,
                "price_snapshot": str(item.price_snapshot),
            }
        )
    return payload


def _apply_inventory_adjustments(items: list[CartItem]) -> list[Product]:
    product_ids = {item.product_id for item in items if item.product_id}
    if not product_ids:
        return []
    locked_inventories = {
        inventory.product_id: inventory
        for inventory in Inventory.objects.select_for_update().filter(product_id__in=product_ids)
    }
    for item in items:
        inventory = locked_inventories.get(item.product_id)
        if inventory is None:
            continue
        if inventory.quantity < item.quantity:
            raise InventoryInsufficientError(
                product_id=item.product_id,
                requested=item.quantity,
                available=inventory.quantity,
            )
    for item in items:
        inventory = locked_inventories.get(item.product_id)
        if inventory is None:
            continue
        Inventory.objects.filter(pk=inventory.pk).update(quantity=F("quantity") - item.quantity)
    products = list(
        Product.objects.select_related("store", "inventory").filter(id__in=product_ids)
    )
    for product in products:
        inventory = getattr(product, "inventory", None)
        if inventory is not None:
            inventory.refresh_from_db(fields=["quantity", "reserved", "updated_at"])
    return products


def _quantize_money(value: Decimal, *, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _resolve_calocoin_conversion(
        *,
        profile: Profile,
        total_rub: Decimal,
        base_currency: str,
) -> tuple[Decimal, dict[str, str]]:
    rate = Decimal(profile.calocoin_rate_rub or 0)
    if rate <= 0:
        raise CartCheckoutError("Курс CaloCoin не настроен. Обратитесь в поддержку.")
    normalized_rate = _quantize_money(rate)
    amount_calo = _quantize_money(total_rub / normalized_rate)
    conversion = {
        "base_currency": base_currency,
        "base_amount": str(_quantize_money(total_rub)),
        "amount_calo": str(amount_calo),
        "rate_rub_per_calo": str(normalized_rate),
    }
    return amount_calo, conversion


def checkout_cart(
        cart: Cart,
        *,
        profile: Profile,
    pay_with_wallet: bool,
    wallet_currency: str | None = None,
    metadata: Mapping[str, object] | None = None,
    rid: str | None = None,
) -> CartCheckoutResult:
    resolved_rid = rid or get_request_id()
    with transaction.atomic():
        locked_cart = (
            Cart.objects.select_for_update()
            .select_related("store")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=CartItem.objects.select_related("product", "product__inventory"),
                )
            )
            .get(pk=cart.pk)
        )
        if locked_cart.user_id != profile.user_id:
            raise CartCheckoutError("Корзина принадлежит другому пользователю")
        if locked_cart.status != Cart.Status.ACTIVE:
            raise CartInactiveError("Корзина уже оформлена или недоступна")
        cart_items = list(locked_cart.items.all())
        if not cart_items:
            raise CartEmptyError("Корзина пуста")

        total_amount = sum((item.price_snapshot * item.quantity for item in cart_items), Decimal("0"))
        total_quantity = sum(item.quantity for item in cart_items)
        requested_wallet = wallet_currency.upper() if isinstance(wallet_currency, str) else None
        currency = _ensure_currency(requested_wallet, locked_cart.currency)
        base_currency = locked_cart.currency or Order.Currency.RUB
        description = _build_order_description(
            (item.product.title for item in cart_items if item.product),
            total_quantity,
        )
        order_metadata = {
            "cart_id": locked_cart.id,
            "store_id": locked_cart.store_id,
            "items": _serialize_items(cart_items),
            "payment": {
                "requested_wallet": requested_wallet,
                "used_wallet": requested_wallet if pay_with_wallet else None,
            },
        }
        if metadata:
            order_metadata["checkout"] = dict(metadata)

        conversion_payload: dict[str, str] | None = None
        effective_amount = total_amount
        if currency == Order.Currency.CALOCOIN:
            effective_amount, conversion_payload = _resolve_calocoin_conversion(
                profile=profile,
                total_rub=total_amount,
                base_currency=base_currency,
            )
            rate_display = Decimal(profile.calocoin_rate_rub or 0)
            hint = (
                f"Цена в рублях: {_quantize_money(total_amount)} {base_currency}"
                f" · Курс {_quantize_money(rate_display)} ₽/CALO"
            )
            description = f"{description}. {hint}"[:255]
        pricing_metadata = {
            "total": str(_quantize_money(effective_amount)),
            "currency": currency,
            "base_total": str(_quantize_money(total_amount)),
            "base_currency": base_currency,
        }
        if conversion_payload:
            pricing_metadata["conversion"] = conversion_payload
            order_metadata.setdefault("payment", {})["conversion"] = conversion_payload

        order = create_order(
            profile,
            title="Покупка товаров на маркетплейсе",
            currency=currency,
            amount=effective_amount,
            description=description,
            kind=Order.Kind.DIGITAL_PRODUCT,
            reference=str(locked_cart.pk),
            metadata={**order_metadata, "pricing": pricing_metadata},
        )
        order.items_count = total_quantity
        order.save(update_fields=["items_count", "updated_at"])

        locked_cart.status = Cart.Status.CHECKED_OUT
        cart_metadata = locked_cart.metadata if isinstance(locked_cart.metadata, dict) else {}
        locked_cart.metadata = {**cart_metadata, "order_id": order.pk}
        locked_cart.save(update_fields=["status", "metadata", "updated_at"])

        was_paid = False
        try:
            if pay_with_wallet:
                order, _ = pay_order_from_wallet(order)
                was_paid = order.status == Order.Status.PAID
        except WalletInsufficientFunds:
            logger.warning(
                "wallet payment failed",
                extra={
                    "rid": resolved_rid,
                    "order_id": order.pk,
                    "cart_id": locked_cart.pk,
                    "currency": currency,
                    "amount": str(order.total_price),
                    "base_amount": str(_quantize_money(total_amount)),
                    "base_currency": base_currency,
                },
            )
            raise

        updated_products: list[Product] = []
        if was_paid:
            payment_meta = order.metadata.get("payment", {}) if isinstance(order.metadata, dict) else {}
            payment_meta.update(
                {
                    "requested_wallet": requested_wallet,
                    "used_wallet": order.wallet_currency or requested_wallet,
                }
            )
            order.metadata = {**order.metadata, "payment": payment_meta} if isinstance(order.metadata, dict) else {
                "payment": payment_meta
            }
            order.save(update_fields=["metadata", "updated_at"])
            updated_products = _apply_inventory_adjustments(cart_items)

        order_data = OrderSerializer(order).data
        transaction.on_commit(
            lambda: publish_market_event(
                "orders",
                {
                    "action": "created",
                    "order": order_data,
                },
                context={"rid": resolved_rid},
            )
        )
        if was_paid:
            paid_payload = OrderSerializer(order).data
            transaction.on_commit(
                lambda: publish_market_event(
                    "orders",
                    {
                        "action": "status_changed",
                        "order": paid_payload,
                    },
                    context={"rid": resolved_rid},
                )
            )
        if updated_products:
            product_snapshots = [
                serialize_instance(product, "apps.market.serializers.ProductSerializer")
                for product in updated_products
            ]
            transaction.on_commit(
                lambda: [
                    publish_market_event(
                        "products",
                        {
                            "action": "updated",
                            "product": snapshot,
                        },
                        context={"rid": resolved_rid},
                    )
                    for snapshot in product_snapshots
                ]
            )

        logger.info(
            "cart checkout completed",
            extra={
                "rid": resolved_rid,
                "order_id": order.pk,
                "cart_id": locked_cart.pk,
                "was_paid": was_paid,
                "currency": currency,
                "amount": str(order.total_price),
                "wallet_currency": order.wallet_currency,
                "items_count": total_quantity,
                "base_amount": str(_quantize_money(total_amount)),
                "base_currency": base_currency,
                "conversion": conversion_payload,
            },
        )

        return CartCheckoutResult(order=order, cart=locked_cart, was_paid=was_paid)


__all__ = [
    "CartCheckoutError",
    "CartInactiveError",
    "CartEmptyError",
    "InventoryInsufficientError",
    "CartCheckoutResult",
    "checkout_cart",
]
