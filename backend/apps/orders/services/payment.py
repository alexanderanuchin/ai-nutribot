from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Union

from django.db import transaction
from django.utils import timezone

from apps.common.logging import summarize_token
from apps.users.models import Profile
from nutribot.middleware import get_build_fingerprint, get_request_id

from ..models import IntegrationWebhookEvent, Order, PaymentAttempt, WalletTransaction
from .order import OrderService, PaymentResult
from .telegram_invoice import (
    TelegramInvoiceResult,
    TelegramStarsInvoiceError,
    TelegramStarsInvoiceService,
)
from .wallet import (
    WalletInsufficientFunds,
    wallet_consume_hold,
    wallet_hold,
    wallet_mark_hold_confirmed,
    wallet_release_hold,
    wallet_topup,
    wallet_withdraw,
)

logger = logging.getLogger("audit.wallet")


class PaymentProviderError(Exception):
    """Base class for provider related errors."""

    def __init__(self, message: str, *, code: str | None = None, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


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
            request_id: str | None = None,
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
    invoice_service_class = TelegramStarsInvoiceService

    def __init__(self, service: "PaymentService", invoice_service: TelegramStarsInvoiceService | None = None) -> None:
        super().__init__(service)
        self.invoice_service = invoice_service or self.invoice_service_class()

    def _ensure_integer_amount(self, amount: Decimal) -> int:
        integer_amount = int(amount)
        if Decimal(integer_amount) != amount:
            raise PaymentProviderError(
                "Сумма для пополнения Stars должна быть целым числом.",
                code="invalid_amount",
            )
        return integer_amount

    def _find_idempotent_attempt(
            self,
            *,
            idempotency_key: str | None,
    ) -> PaymentAttempt | None:
        if not idempotency_key:
            return None
        return (
            PaymentAttempt.objects.filter(
                provider=self.code,
                confirmation_payload__idempotency_key=idempotency_key,
            )
            .order_by("-initiated_at", "-id")
            .first()
        )

    def start_wallet_topup(
            self,
            profile: Profile,
            *,
            currency: str,
            amount: Decimal,
            idempotency_key: str | None,
            metadata: Dict[str, Any] | None = None,
            request_id: str | None = None,
    ) -> PaymentInitiationResult:
        if currency != WalletTransaction.Currency.TELEGRAM_STARS:
            raise PaymentProviderError("Telegram Stars provider принимает только валюту STARS", code="invalid_currency")

        existing = self._find_idempotent_attempt(idempotency_key=idempotency_key)
        if existing:
            confirmation = existing.confirmation_payload or {}
            return PaymentInitiationResult(payment_attempt=existing, confirmation_data=confirmation)

        integer_amount = self._ensure_integer_amount(amount)
        external_payment_id = uuid.uuid4().hex
        confirmation_payload: Dict[str, Any] = {
            "invoice_id": external_payment_id,
            "profile_id": profile.pk,
            "metadata": metadata or {},
            "idempotency_key": idempotency_key,
        }
        attempt = PaymentAttempt.objects.create(
            provider=self.code,
            status=PaymentAttempt.Status.INITIATED,
            amount=amount,
            currency=currency,
            external_payment_id=external_payment_id,
            confirmation_payload=confirmation_payload,
        )

        try:
            invoice: TelegramInvoiceResult = self.invoice_service.create_wallet_topup_invoice(
                profile=profile,
                amount_stars=integer_amount,
                comment=(metadata or {}).get("comment") if metadata else None,
                metadata={"payment_attempt_id": attempt.pk, **(metadata or {})},
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
        except TelegramStarsInvoiceError as exc:
            if exc.details.get("block_purchases"):
                Profile.objects.filter(pk=profile.pk).update(
                    stars_purchase_blocked=True,
                    updated_at=timezone.now(),
                )
                profile.stars_purchase_blocked = True
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.failure_code = exc.code or "invoice_error"
            attempt.failure_reason = str(exc)
            attempt.processed_at = timezone.now()
            attempt.save(update_fields=[
                "status",
                "failure_code",
                "failure_reason",
                "processed_at",
                "updated_at",
            ])
            raise PaymentProviderError(str(exc), code=exc.code, details=exc.details) from exc

        confirmation = {
            "invoice_id": external_payment_id,
            "invoice_link": invoice.invoice_link,
            "payload": invoice.payload,
            "profile_id": profile.pk,
            "telegram_user_id": profile.telegram_id,
            "metadata": metadata or {},
            "idempotency_key": idempotency_key,
            "title": invoice.title,
            "description": invoice.description,
            "start_parameter": invoice.start_parameter,
        }
        attempt.confirmation_payload = confirmation
        attempt.save(update_fields=["confirmation_payload", "updated_at"])
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
            request_id: str | None = None,
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
            request_id: str | None = None,
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

    @staticmethod
    def _resolve_profile(user: Profile | Any) -> Profile:
        if isinstance(user, Profile):
            return user
        profile = getattr(user, "profile", None)
        if isinstance(profile, Profile):
            return profile
        raise PaymentProviderError("Профиль пользователя не найден")

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
            request_id: str | None = None,
    ) -> PaymentInitiationResult:
        provider_instance = self.get_provider(provider)
        return provider_instance.start_wallet_topup(
            profile,
            currency=currency,
            amount=amount,
            idempotency_key=idempotency_key,
            metadata=metadata,
            request_id=request_id,
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

    def wallet_topup(
            self,
            user: Union[Profile, Any],
            *,
            amount: Decimal,
            charge_id: str,
            idempotency_key: str | None = None,
            metadata: Dict[str, Any] | None = None,
    ) -> WalletTransaction:
        profile = self._resolve_profile(user)
        if getattr(profile, "stars_purchase_blocked", False):
            raise PaymentProviderError(
                "Telegram сообщает, что пополнения Stars недоступны в вашем регионе.",
                code="purchases_disabled",
                details={"block_purchases": True},
            )
        meta = {
            "source": "telegram_bot_invoice",
            "telegram_payment_charge_id": charge_id,
            **(metadata or {}),
        }
        key = idempotency_key or charge_id
        rid = get_request_id()
        logger.info(
            "payment_service wallet_topup start",
            extra={
                "rid": rid,
                "request_id": rid,
                "build_fingerprint": get_build_fingerprint(),
                "profile_id": getattr(profile, "id", None),
                "telegram_user_id": getattr(profile, "telegram_id", None),
                "amount": str(amount),
                "currency": WalletTransaction.Currency.TELEGRAM_STARS,
                "charge_id": summarize_token(charge_id),
                "idempotency_key": key,
                "has_comment": bool((metadata or {}).get("comment")),
            },
        )
        tx = wallet_topup(
            profile,
            currency=WalletTransaction.Currency.TELEGRAM_STARS,
            amount=amount,
            description="Пополнение Stars через Telegram",
            reference=charge_id,
            metadata=meta,
            idempotency_key=key,
        )
        logger.info(
            "payment_service wallet_topup done",
            extra={
                "rid": rid,
                "request_id": rid,
                "build_fingerprint": get_build_fingerprint(),
                "profile_id": getattr(profile, "id", None),
                "transaction_id": getattr(tx, "id", None),
                "amount": str(amount),
                "currency": WalletTransaction.Currency.TELEGRAM_STARS,
            },
        )
        return tx

    def wallet_withdraw(
            self,
            user: Union[Profile, Any],
            *,
            amount: Decimal,
            idempotency_key: str | None = None,
            description: str | None = None,
            reference: str | None = None,
            metadata: Dict[str, Any] | None = None,
    ) -> WalletTransaction:
        profile = self._resolve_profile(user)
        try:
            return wallet_withdraw(
                profile,
                currency=WalletTransaction.Currency.TELEGRAM_STARS,
                amount=amount,
                description=description or "Списание Stars",
                reference=reference,
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
        except WalletInsufficientFunds as exc:
            raise PaymentProviderError(str(exc)) from exc

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
