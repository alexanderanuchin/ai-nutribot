from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from apps.users.models import Profile

from .models import Order, WalletPerk, WalletTarget, WalletTransaction

STARS_CONSULTATION_TARGET = Decimal("500")
CALO_PRO_TARGET = Decimal("1200")

_DEFAULT_WALLET_PERKS = [
    "Эксклюзивные планы питания с адаптацией под ваши тренировки",
    "Доступ к мини-курсам и лайв-сессиям нутрициологов каждую неделю",
    "Экспериментальные фичи AI-куратора без ограничений",
]

_DEFAULT_TARGETS: Dict[str, Dict[str, Any]] = {
    WalletTransaction.Currency.TELEGRAM_STARS: {
        "label": "До клубной консультации",
        "target": STARS_CONSULTATION_TARGET,
        "progress_template": "Ещё {left} Stars — и куратор свяжется с вами.",
        "completed_template": "Доступ к консультациям открыт — напишите куратору в @CaloIQ_bot.",
    },
    WalletTransaction.Currency.CALOCOIN: {
        "label": "До PRO-доступа",
        "target": CALO_PRO_TARGET,
        "progress_template": "Накопите ещё {left} CaloCoin для полного PRO.",
        "completed_template": "Баланс позволяет активировать PRO прямо сейчас.",
    },
}


def _quant_for_currency(currency: str) -> Decimal:
    if currency == WalletTransaction.Currency.TELEGRAM_STARS:
        return Decimal("1")
    return Decimal("0.01")


def _normalize_amount(currency: str, amount: Any) -> Decimal:
    if isinstance(amount, Decimal):
        value = amount
    else:
        value = Decimal(str(amount))
    if value <= 0:
        raise ValueError("Amount must be positive")
    quant = _quant_for_currency(currency)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _profile_balance(profile: Profile, currency: str) -> Decimal:
    if currency == WalletTransaction.Currency.TELEGRAM_STARS:
        return Decimal(profile.telegram_stars_balance or 0)
    return Decimal(profile.calocoin_balance or 0)


def _set_profile_balance(profile: Profile, currency: str, balance: Decimal) -> None:
    quant = _quant_for_currency(currency)
    normalized = balance.quantize(quant, rounding=ROUND_HALF_UP)
    if currency == WalletTransaction.Currency.TELEGRAM_STARS:
        profile.telegram_stars_balance = int(normalized)
        profile.save(update_fields=["telegram_stars_balance", "updated_at"])
    else:
        profile.calocoin_balance = normalized
        profile.save(update_fields=["calocoin_balance", "updated_at"])


def wallet_topup(
    profile: Profile,
    *,
    currency: str,
    amount: Any,
    description: str | None = None,
    reference: str | None = None,
    metadata: Dict[str, Any] | None = None,
    related_order: Order | None = None,
) -> WalletTransaction:
    normalized_amount = _normalize_amount(currency, amount)
    meta = metadata or {}
    with transaction.atomic():
        locked = Profile.objects.select_for_update().get(pk=profile.pk)
        balance_before = _profile_balance(locked, currency)
        balance_after = balance_before + normalized_amount
        _set_profile_balance(locked, currency, balance_after)
        transaction_record = WalletTransaction.objects.create(
            profile=locked,
            currency=currency,
            direction=WalletTransaction.Direction.CREDIT,
            amount=normalized_amount,
            balance_before=balance_before.quantize(_quant_for_currency(currency)),
            balance_after=balance_after.quantize(_quant_for_currency(currency)),
            description=description or "Пополнение баланса",
            reference=reference or "",
            metadata=meta,
            related_order=related_order,
        )
        return transaction_record


def wallet_withdraw(
    profile: Profile,
    *,
    currency: str,
    amount: Any,
    description: str | None = None,
    reference: str | None = None,
    metadata: Dict[str, Any] | None = None,
    related_order: Order | None = None,
) -> WalletTransaction:
    normalized_amount = _normalize_amount(currency, amount)
    meta = metadata or {}
    with transaction.atomic():
        locked = Profile.objects.select_for_update().get(pk=profile.pk)
        balance_before = _profile_balance(locked, currency)
        if balance_before < normalized_amount:
            raise ValueError("Недостаточно средств для списания")
        balance_after = balance_before - normalized_amount
        _set_profile_balance(locked, currency, balance_after)
        transaction_record = WalletTransaction.objects.create(
            profile=locked,
            currency=currency,
            direction=WalletTransaction.Direction.DEBIT,
            amount=normalized_amount,
            balance_before=balance_before.quantize(_quant_for_currency(currency)),
            balance_after=balance_after.quantize(_quant_for_currency(currency)),
            description=description or "Списание средств",
            reference=reference or "",
            metadata=meta,
            related_order=related_order,
        )
        return transaction_record


def create_order(
    profile: Profile,
    *,
    title: str,
    currency: str,
    amount: Any,
    description: str | None = None,
    kind: str | None = None,
    reference: str | None = None,
    metadata: Dict[str, Any] | None = None,
    status: str | None = None,
) -> Order:
    normalized_amount = _normalize_amount(currency, amount)
    meta = metadata or {}
    order = Order.objects.create(
        user=profile.user,
        profile=profile,
        title=title,
        currency=currency,
        amount=normalized_amount,
        description=description or "",
        kind=kind or Order.Kind.PRO_SUBSCRIPTION,
        reference=reference or "",
        metadata=meta,
        status=status or Order.Status.PENDING_PAYMENT,
    )
    return order


def pay_order_from_wallet(
    order: Order,
    *,
    description: str | None = None,
    reference: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Tuple[Order, WalletTransaction]:
    if order.is_paid:
        return order, order.payment_transaction  # type: ignore[return-value]
    meta = metadata or {}
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.is_paid:
            return locked, locked.payment_transaction  # type: ignore[return-value]
        tx = wallet_withdraw(
            locked.profile,
            currency=locked.currency,
            amount=locked.total_price,
            description=description or f"Оплата заказа #{locked.pk}",
            reference=reference or locked.reference,
            metadata={**meta, "order_id": locked.pk},
        )
        locked.payment_transaction = tx
        locked.status = Order.Status.PAID
        locked.wallet_currency = locked.wallet_currency or locked.currency
        locked.paid_at = timezone.now()
        locked.save(update_fields=["payment_transaction", "status", "paid_at", "updated_at"])
        return locked, tx


def _format_decimal(value: Decimal, currency: str) -> float | int:
    if currency == WalletTransaction.Currency.TELEGRAM_STARS:
        return int(value)
    quant = _quant_for_currency(currency)
    return float(value.quantize(quant, rounding=ROUND_HALF_UP))


def _format_value_for_message(value: Decimal, currency: str) -> str:
    quant = _quant_for_currency(currency)
    normalized = value.quantize(quant, rounding=ROUND_HALF_UP)
    if quant == Decimal("1"):
        return str(int(normalized))
    normalized = normalized.normalize()
    return format(normalized, "f")


def _render_target_message(template: str | None, *, currency: str, left: Decimal, target: Decimal, balance: Decimal, progress: int) -> str:
    if not template:
        return ""
    replacements = {
        "left": _format_value_for_message(left, currency),
        "target": _format_value_for_message(target, currency),
        "balance": _format_value_for_message(balance, currency),
        "currency": currency,
        "progress": str(progress),
    }
    try:
        return template.format(**replacements)
    except (KeyError, ValueError):
        return template


def _resolve_target_configs(profile: Profile) -> Dict[str, Dict[str, Any]]:
    base: Dict[str, Dict[str, Any]] = {}
    for currency, defaults in _DEFAULT_TARGETS.items():
        base[currency] = {
            "target": defaults["target"],
            "label": defaults.get("label", ""),
            "progress_template": defaults.get("progress_template", ""),
            "completed_template": defaults.get("completed_template", ""),
        }

    queryset = (
        WalletTarget.objects.filter(profile=profile, is_active=True)
        .order_by("priority", "currency", "-updated_at")
    )
    seen: Dict[str, WalletTarget] = {}
    for target in queryset:
        if target.currency in seen:
            continue
        seen[target.currency] = target

    for currency, target in seen.items():
        config = base.get(currency, {
            "target": target.target_amount,
            "label": target.get_currency_display(),
            "progress_template": "",
            "completed_template": "",
        })
        config = config.copy()
        config["target"] = target.target_amount
        if target.label:
            config["label"] = target.label
        if target.progress_template:
            config["progress_template"] = target.progress_template
        if target.completed_template:
            config["completed_template"] = target.completed_template
        base[currency] = config

    return base


def _build_target_payload(currency: str, balance: Decimal, config: Dict[str, Any]) -> Dict[str, Any]:
    quant = _quant_for_currency(currency)
    target_amount = config.get("target", Decimal("0"))
    if not isinstance(target_amount, Decimal):
        target_amount = Decimal(str(target_amount))
    if target_amount < 0:
        target_amount = Decimal("0")
    target_amount = target_amount.quantize(quant, rounding=ROUND_HALF_UP)
    balance_value = balance.quantize(quant, rounding=ROUND_HALF_UP)
    left_value = (target_amount - balance_value)
    if left_value < 0:
        left_value = Decimal("0")
    left_value = left_value.quantize(quant, rounding=ROUND_HALF_UP)

    if target_amount > 0:
        ratio = (balance_value / target_amount) * Decimal("100")
        progress_decimal = min(Decimal("100"), ratio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        progress = int(progress_decimal)
    else:
        progress = 100 if balance_value > 0 else 0

    payload: Dict[str, Any] = {
        "target": _format_decimal(target_amount, currency),
        "balance": _format_decimal(balance_value, currency),
        "progress": progress,
        "left": _format_decimal(left_value, currency),
    }

    label = config.get("label") or _DEFAULT_TARGETS.get(currency, {}).get("label")
    if label:
        payload["label"] = label

    progress_template = config.get("progress_template") or _DEFAULT_TARGETS.get(currency, {}).get("progress_template")
    completed_template = config.get("completed_template") or _DEFAULT_TARGETS.get(currency, {}).get("completed_template")

    progress_message = _render_target_message(
        progress_template,
        currency=currency,
        left=left_value,
        target=target_amount,
        balance=balance_value,
        progress=progress,
    )
    completed_message = _render_target_message(
        completed_template,
        currency=currency,
        left=left_value,
        target=target_amount,
        balance=balance_value,
        progress=progress,
    )
    if progress_message:
        payload["progress_message"] = progress_message
    if completed_message:
        payload["completed_message"] = completed_message

    return payload


def _resolve_wallet_perks(profile: Profile) -> list[str]:
    perks = [
        perk.display_text.strip()
        for perk in WalletPerk.objects.filter(profile=profile, is_active=True)
        .order_by("priority", "id")
        if perk.display_text.strip()
    ]
    if perks:
        return perks
    return list(_DEFAULT_WALLET_PERKS)


def _serialize_transaction(tx: WalletTransaction) -> Dict[str, Any]:
    return {
        "id": tx.pk,
        "currency": tx.currency.lower(),
        "direction": tx.direction,
        "amount": _format_decimal(tx.amount, tx.currency),
        "balance_after": _format_decimal(tx.balance_after, tx.currency),
        "balance_before": _format_decimal(tx.balance_before, tx.currency),
        "description": tx.description,
        "reference": tx.reference or None,
        "metadata": tx.metadata,
        "created_at": tx.created_at.isoformat(),
    }


def _serialize_order(order: Order) -> Dict[str, Any]:
    return {
        "id": order.pk,
        "title": order.title,
        "status": order.status,
        "status_display": order.get_status_display(),
        "currency": order.currency.lower(),
        "amount": _format_decimal(order.total_price, order.currency),
        "description": order.description or "",
        "reference": order.reference or None,
        "kind": order.kind,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "created_at": order.created_at.isoformat(),
    }


def build_wallet_summary(
    profile: Profile,
    *,
    transactions_limit: int = 5,
    orders_limit: int = 3,
) -> Dict[str, Any]:
    balances: Dict[str, Decimal] = {
        WalletTransaction.Currency.TELEGRAM_STARS: Decimal(profile.telegram_stars_balance or 0),
        WalletTransaction.Currency.CALOCOIN: Decimal(profile.calocoin_balance or 0),
    }

    target_configs = _resolve_target_configs(profile)

    targets_payload: Dict[str, Any] = {}
    for currency, config in target_configs.items():
        balance = balances.get(currency, Decimal("0"))
        targets_payload[currency.lower()] = _build_target_payload(currency, balance, config)

    transactions = list(
        WalletTransaction.objects.filter(profile=profile)
        .order_by("-created_at", "-id")
        [:transactions_limit]
    )
    orders = list(
        Order.objects.filter(profile=profile)
        .order_by("-created_at", "-id")
        [:orders_limit]
    )

    return {
        "perks": _resolve_wallet_perks(profile),
        "targets": targets_payload,
        "recent_transactions": [_serialize_transaction(tx) for tx in transactions],
        "recent_orders": [_serialize_order(order) for order in orders],
    }


__all__ = [
    "wallet_topup",
    "wallet_withdraw",
    "create_order",
    "pay_order_from_wallet",
    "build_wallet_summary",
    "STARS_CONSULTATION_TARGET",
    "CALO_PRO_TARGET",
]