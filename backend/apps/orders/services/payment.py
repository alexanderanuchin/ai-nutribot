from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict
import uuid

from django.db import transaction
from django.utils import timezone

from apps.users.models import Profile

from ..models import IntegrationWebhookEvent, Order, PaymentAttempt, WalletTransaction
from .order import OrderService, PaymentResult
from .wallet import (
    WalletInsufficientFunds,
    wallet_consume_hold,
    wallet_hold,
    wallet_mark_hold_confirmed,
    wallet_release_hold,
    wallet_topup,
)


class PaymentProviderError(Exception):
    """Base class for provider related errors."""


@dataclass
class PaymentInitiationResult:
    payment_attempt: PaymentAttempt
    confirmation_data: Dict[str, Any]


class BasePaymentProvider:
    code: str

    def __init__(self, service: "PaymentService") -> None:
        self.service = service

    # -- Wallet top ups -------------------------------------------------
    def start_wallet_topup(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentInitiationResult:
        raise NotImplementedError

    # -- Order payments -------------------------------------------------
    def start_order_payment(
        self,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        raise NotImplementedError

    # -- Webhooks -------------------------------------------------------
    def handle_webhook(
        self,
        payload: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IntegrationWebhookEvent:
        raise NotImplementedError


class TelegramStarsProvider(BasePaymentProvider):
    code = PaymentAttempt.Provider.TELEGRAM_STARS

    def start_wallet_topup(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentInitiationResult:
        if currency != WalletTransaction.Currency.TELEGRAM_STARS:
            raise PaymentProviderError("Telegram Stars provider accepts only STARS currency")
        external_payment_id = uuid.uuid4().hex
        attempt = PaymentAttempt.objects.create(
            provider=self.code,
            status=PaymentAttempt.Status.INITIATED,
            amount=amount,
            currency=currency,
            external_payment_id=external_payment_id,
            confirmation_payload={
                "invoice_id": external_payment_id,
                "profile_id": profile.pk,
                "metadata": metadata or {},
            },
        )
        confirmation = {
            "invoice_id": external_payment_id,
            "payload": {
                "amount": int(amount),
                "currency": currency,
            },
        }
        return PaymentInitiationResult(payment_attempt=attempt, confirmation_data=confirmation)

    def start_order_payment(
        self,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        if currency != WalletTransaction.Currency.TELEGRAM_STARS:
            raise PaymentProviderError("Telegram Stars order payment must be in STARS")
        external_payment_id = uuid.uuid4().hex
        attempt = PaymentAttempt.objects.create(
            order=order,
            provider=self.code,
            status=PaymentAttempt.Status.INITIATED,
            amount=amount,
            currency=currency,
            external_payment_id=external_payment_id,
            confirmation_payload={
                "invoice_id": external_payment_id,
                "order_id": order.pk,
                "metadata": metadata or {},
            },
        )
        return attempt

    def handle_webhook(
        self,
        payload: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IntegrationWebhookEvent:
        external_payment_id = str(payload.get("external_payment_id"))
        status = payload.get("status")
        amount = Decimal(str(payload.get("amount", "0")))
        currency = payload.get("currency", WalletTransaction.Currency.TELEGRAM_STARS)
        profile_id = payload.get("profile_id")
        order_id = payload.get("order_id")
        charge_id = payload.get("telegram_payment_charge_id")

        attempt = PaymentAttempt.objects.filter(
            provider=self.code, external_payment_id=external_payment_id
        ).select_related("order").first()
        event, created = IntegrationWebhookEvent.objects.get_or_create(
            source=IntegrationWebhookEvent.Source.PAYMENT,
            external_event_id=external_payment_id,
            defaults={
                "event_type": "telegram_stars.payment",
                "payload": payload,
                "related_payment": attempt,
                "status": IntegrationWebhookEvent.ProcessingStatus.RECEIVED,
            },
        )
        if not created:
            return event

        if not attempt:
            event.status = IntegrationWebhookEvent.ProcessingStatus.FAILED
            event.error_details = "PaymentAttempt not found"
            event.save(update_fields=["status", "error_details", "updated_at"])
            return event

        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            event.status = IntegrationWebhookEvent.ProcessingStatus.PROCESSED
            event.processed_at = timezone.now()
            event.save(update_fields=["status", "processed_at", "updated_at"])
            return event

        with transaction.atomic():
            locked_attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
            if locked_attempt.status == PaymentAttempt.Status.SUCCEEDED:
                event.status = IntegrationWebhookEvent.ProcessingStatus.PROCESSED
                event.processed_at = timezone.now()
                event.save(update_fields=["status", "processed_at", "updated_at"])
                return event

            profile = None
            if profile_id:
                profile = Profile.objects.select_for_update().get(pk=profile_id)
            elif locked_attempt.order_id:
                profile = locked_attempt.order.profile

            if status == "succeeded":
                wallet_tx = None
                if profile:
                    wallet_tx = wallet_topup(
                        profile,
                        currency=currency,
                        amount=amount,
                        description="Пополнение Stars через Telegram",
                        reference=charge_id,
                        metadata={
                            "source": "telegram_webhook",
                            "attempt_id": locked_attempt.pk,
                            "external_payment_id": external_payment_id,
                            "telegram_payment_charge_id": charge_id,
                        },
                        idempotency_key=idempotency_key or external_payment_id,
                    )
                locked_attempt.wallet_transaction = wallet_tx
                locked_attempt.save(update_fields=["wallet_transaction", "updated_at"])
                if locked_attempt.order_id:
                    order_service = OrderService(locked_attempt.order)
                    order_service.apply_payment_result(
                        locked_attempt,
                        PaymentResult(
                            success=True,
                            wallet_transaction=wallet_tx,
                            wallet_currency=WalletTransaction.Currency.TELEGRAM_STARS,
                        ),
                        webhook_event=event,
                    )
                    locked_attempt.refresh_from_db()
                else:
                    event.status = IntegrationWebhookEvent.ProcessingStatus.PROCESSED
                    event.processed_at = timezone.now()
                    event.related_payment = locked_attempt
                    event.save(update_fields=["status", "processed_at", "related_payment", "updated_at"])
            else:
                locked_attempt.status = PaymentAttempt.Status.FAILED
                locked_attempt.failure_code = payload.get("error_code", "unknown")
                locked_attempt.failure_reason = payload.get("error_message", "Payment failed")
                locked_attempt.processed_at = timezone.now()
                locked_attempt.save(update_fields=[
                    "status",
                    "failure_code",
                    "failure_reason",
                    "processed_at",
                    "updated_at",
                ])
                event.status = IntegrationWebhookEvent.ProcessingStatus.FAILED
                event.error_details = locked_attempt.failure_reason
                event.processed_at = timezone.now()
                event.related_payment = locked_attempt
                event.save(update_fields=[
                    "status",
                    "error_details",
                    "processed_at",
                    "related_payment",
                    "updated_at",
                ])
        return event


class CaloCoinProvider(BasePaymentProvider):
    code = PaymentAttempt.Provider.CALOCOIN

    def start_wallet_topup(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentInitiationResult:
        raise PaymentProviderError("CaloCoin provider does not support direct top ups")

    def start_order_payment(
        self,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        if currency != WalletTransaction.Currency.CALOCOIN:
            raise PaymentProviderError("CaloCoin provider handles CALO payments only")
        try:
            hold_tx = wallet_hold(
                order.profile,
                currency=currency,
                amount=amount,
                description=f"Резерв под заказ #{order.pk}",
                metadata={"order_id": order.pk, **(metadata or {})},
                related_order=order,
                idempotency_key=idempotency_key,
            )
        except WalletInsufficientFunds as exc:
            raise PaymentProviderError(str(exc)) from exc

        wallet_mark_hold_confirmed(hold_tx)
        attempt = PaymentAttempt.objects.create(
            order=order,
            provider=self.code,
            status=PaymentAttempt.Status.PENDING,
            amount=amount,
            currency=currency,
            wallet_transaction=hold_tx,
            external_payment_id=str(hold_tx.pk),
            confirmation_payload={"hold_id": hold_tx.pk},
        )
        return attempt

    def handle_webhook(
        self,
        payload: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IntegrationWebhookEvent:
        raise PaymentProviderError("Internal CaloCoin provider does not accept webhooks")

    def capture(
        self,
        payment_attempt: PaymentAttempt,
        *,
        idempotency_key: str | None = None,
    ) -> PaymentAttempt:
        if payment_attempt.provider != self.code:
            raise PaymentProviderError("Attempt does not belong to CaloCoin provider")
        if not payment_attempt.wallet_transaction:
            raise PaymentProviderError("Missing hold transaction")
        if payment_attempt.status == PaymentAttempt.Status.SUCCEEDED:
            return payment_attempt
        debit_tx = wallet_consume_hold(
            payment_attempt.wallet_transaction,
            description=f"Оплата заказа #{payment_attempt.order_id}",
            metadata={"payment_attempt_id": payment_attempt.pk},
            idempotency_key=idempotency_key,
        )
        payment_attempt.wallet_transaction = debit_tx
        payment_attempt.save(update_fields=["wallet_transaction", "updated_at"])
        OrderService(payment_attempt.order).apply_payment_result(
            payment_attempt,
            PaymentResult(
                success=True,
                wallet_transaction=debit_tx,
                wallet_currency=WalletTransaction.Currency.CALOCOIN,
            ),
        )
        payment_attempt.refresh_from_db()
        payment_attempt.order.refresh_from_db()
        return payment_attempt

    def cancel(
        self,
        payment_attempt: PaymentAttempt,
        *,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentAttempt:
        if payment_attempt.provider != self.code:
            raise PaymentProviderError("Attempt does not belong to CaloCoin provider")
        if payment_attempt.status in {PaymentAttempt.Status.CANCELLED, PaymentAttempt.Status.FAILED}:
            return payment_attempt
        if payment_attempt.wallet_transaction:
            wallet_release_hold(
                payment_attempt.wallet_transaction,
                reason=reason or "Отмена оплаты заказа",
                metadata={"payment_attempt_id": payment_attempt.pk},
                idempotency_key=idempotency_key,
            )
        payment_attempt.status = PaymentAttempt.Status.CANCELLED
        payment_attempt.failure_reason = reason or payment_attempt.failure_reason
        payment_attempt.processed_at = timezone.now()
        payment_attempt.save(update_fields=[
            "status",
            "failure_reason",
            "processed_at",
            "updated_at",
        ])
        return payment_attempt


class CardProvider(BasePaymentProvider):
    code = PaymentAttempt.Provider.CARD

    def start_wallet_topup(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentInitiationResult:
        external_payment_id = uuid.uuid4().hex
        attempt = PaymentAttempt.objects.create(
            provider=self.code,
            status=PaymentAttempt.Status.INITIATED,
            amount=amount,
            currency=currency,
            external_payment_id=external_payment_id,
            confirmation_payload={
                "payment_url": f"https://pay.local/{external_payment_id}",
                "profile_id": profile.pk,
                "metadata": metadata or {},
            },
        )
        confirmation = {
            "payment_url": attempt.confirmation_payload["payment_url"],
            "external_payment_id": external_payment_id,
        }
        return PaymentInitiationResult(payment_attempt=attempt, confirmation_data=confirmation)

    def start_order_payment(
        self,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        idempotency_key: str | None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        raise PaymentProviderError("Card provider is only for wallet top ups")

    def handle_webhook(
        self,
        payload: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IntegrationWebhookEvent:
        external_payment_id = str(payload.get("external_payment_id"))
        status = payload.get("status")
        amount = Decimal(str(payload.get("amount", "0")))
        currency = payload.get("currency")
        attempt = PaymentAttempt.objects.filter(
            provider=self.code, external_payment_id=external_payment_id
        ).first()
        event, created = IntegrationWebhookEvent.objects.get_or_create(
            source=IntegrationWebhookEvent.Source.PAYMENT,
            external_event_id=external_payment_id,
            defaults={
                "event_type": "card.payment",
                "payload": payload,
                "related_payment": attempt,
                "status": IntegrationWebhookEvent.ProcessingStatus.RECEIVED,
            },
        )
        if not created:
            return event

        if not attempt:
            event.status = IntegrationWebhookEvent.ProcessingStatus.FAILED
            event.error_details = "PaymentAttempt not found"
            event.save(update_fields=["status", "error_details", "updated_at"])
            return event

        with transaction.atomic():
            locked_attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
            if status == "succeeded":
                profile_id = payload.get("profile_id")
                profile = Profile.objects.select_for_update().get(pk=profile_id)
                wallet_tx = wallet_topup(
                    profile,
                    currency=currency,
                    amount=amount,
                    description="Пополнение через карту",
                    metadata={"payment_attempt_id": locked_attempt.pk},
                    idempotency_key=idempotency_key or external_payment_id,
                )
                locked_attempt.status = PaymentAttempt.Status.SUCCEEDED
                locked_attempt.wallet_transaction = wallet_tx
                locked_attempt.processed_at = timezone.now()
                locked_attempt.save(update_fields=[
                    "status",
                    "wallet_transaction",
                    "processed_at",
                    "updated_at",
                ])
                event.status = IntegrationWebhookEvent.ProcessingStatus.PROCESSED
                event.processed_at = timezone.now()
                event.related_payment = locked_attempt
                event.save(update_fields=["status", "processed_at", "related_payment", "updated_at"])
            else:
                locked_attempt.status = PaymentAttempt.Status.FAILED
                locked_attempt.failure_code = payload.get("error_code", "unknown")
                locked_attempt.failure_reason = payload.get("error_message", "Card payment failed")
                locked_attempt.processed_at = timezone.now()
                locked_attempt.save(update_fields=[
                    "status",
                    "failure_code",
                    "failure_reason",
                    "processed_at",
                    "updated_at",
                ])
                event.status = IntegrationWebhookEvent.ProcessingStatus.FAILED
                event.error_details = locked_attempt.failure_reason
                event.processed_at = timezone.now()
                event.related_payment = locked_attempt
                event.save(update_fields=[
                    "status",
                    "error_details",
                    "processed_at",
                    "related_payment",
                    "updated_at",
                ])
        return event


class PaymentService:
    """Facade for payment providers and wallet interactions."""

    def __init__(self) -> None:
        self._providers: Dict[str, BasePaymentProvider] = {}
        self.register_provider(TelegramStarsProvider(self))
        self.register_provider(CaloCoinProvider(self))
        self.register_provider(CardProvider(self))

    def register_provider(self, provider: BasePaymentProvider) -> None:
        self._providers[provider.code] = provider

    def get_provider(self, code: str) -> BasePaymentProvider:
        if code not in self._providers:
            raise PaymentProviderError(f"Provider {code} is not registered")
        return self._providers[code]

    def start_wallet_topup(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        provider: str,
        idempotency_key: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentInitiationResult:
        provider_instance = self.get_provider(provider)
        return provider_instance.start_wallet_topup(
            profile,
            currency=currency,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    def start_order_payment(
        self,
        order: Order,
        *,
        currency: str,
        amount: Decimal,
        provider: str,
        idempotency_key: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        provider_instance = self.get_provider(provider)
        attempt = provider_instance.start_order_payment(
            order,
            currency=currency,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        return attempt

    def complete_calocoin_payment(
        self,
        payment_attempt: PaymentAttempt,
        *,
        idempotency_key: str | None = None,
    ) -> PaymentAttempt:
        provider = self.get_provider(PaymentAttempt.Provider.CALOCOIN)
        assert isinstance(provider, CaloCoinProvider)
        return provider.capture(payment_attempt, idempotency_key=idempotency_key)

    def cancel_calocoin_payment(
        self,
        payment_attempt: PaymentAttempt,
        *,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentAttempt:
        provider = self.get_provider(PaymentAttempt.Provider.CALOCOIN)
        assert isinstance(provider, CaloCoinProvider)
        return provider.cancel(payment_attempt, reason=reason, idempotency_key=idempotency_key)

    def manual_credit(
        self,
        profile: Profile,
        *,
        currency: str,
        amount: Decimal,
        source: str,
        idempotency_key: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> WalletTransaction:
        description = f"Ручное пополнение ({source})"
        meta = {"source": source, **(metadata or {})}
        return wallet_topup(
            profile,
            currency=currency,
            amount=amount,
            description=description,
            metadata=meta,
            idempotency_key=idempotency_key,
        )

    def handle_webhook(
        self,
        provider: str,
        payload: Dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> IntegrationWebhookEvent:
        provider_instance = self.get_provider(provider)
        return provider_instance.handle_webhook(payload, idempotency_key=idempotency_key)


__all__ = [
    "PaymentService",
    "PaymentProviderError",
    "PaymentInitiationResult",
]