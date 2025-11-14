from __future__ import annotations

import logging
import textwrap
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LabeledPrice
from asgiref.sync import async_to_sync
from django.conf import settings

from nutribot.middleware import get_build_fingerprint, get_request_id

logger = logging.getLogger("audit.telegram.invoice")


@dataclass(slots=True)
class TelegramInvoiceResult:
    """Represents an invoice link generated via Bot API."""

    invoice_link: str
    payload: str
    title: str
    description: str
    start_parameter: str | None


class TelegramStarsInvoiceError(Exception):
    """Raised when Telegram invoice generation fails."""

    def __init__(self, message: str, *, code: str | None = None, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class TelegramStarsInvoiceService:
    """Wrapper around Bot API `createInvoiceLink` for wallet top-ups."""

    currency_code = "XTR"

    def __init__(self, *, bot_token: str | None = None, provider_token: str | None = None) -> None:
        self._bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        if not self._bot_token:
            raise TelegramStarsInvoiceError(
                "TELEGRAM_BOT_TOKEN is not configured", code="configuration_error"
            )
        self._provider_token = provider_token or settings.TELEGRAM_PROVIDER_TOKEN or ""

    async def _create_invoice_link(
            self,
            *,
            title: str,
            description: str,
            payload: str,
            amount: int,
    ) -> str:
        async with Bot(token=self._bot_token) as bot:
            prices = [LabeledPrice(label=title, amount=amount)]
            return await bot.create_invoice_link(
                title=title,
                description=description,
                payload=payload,
                currency=self.currency_code,
                prices=prices,
                provider_token=self._provider_token,
            )

    def create_wallet_topup_invoice(
            self,
            *,
            profile: "Profile",
            amount_stars: int,
            comment: str | None,
            metadata: Dict[str, Any] | None,
            idempotency_key: str | None,
            request_id: str | None,
    ) -> TelegramInvoiceResult:
        from apps.users.models import Profile  # Local import to avoid circular dependency

        if not isinstance(profile, Profile):
            raise TelegramStarsInvoiceError("Profile instance required", code="invalid_profile")
        if not profile.telegram_id:
            raise TelegramStarsInvoiceError("Telegram ID is required to generate invoice", code="missing_telegram_id")
        if amount_stars <= 0:
            raise TelegramStarsInvoiceError("Amount must be positive", code="invalid_amount")

        rid = request_id or get_request_id() or uuid.uuid4().hex
        comment_text = (comment or "").strip()
        if comment_text:
            comment_text = textwrap.shorten(comment_text, width=180, placeholder="…")

        title = "Пополнение баланса Stars"
        description = f"Быстрое пополнение на {amount_stars} XTR."
        if comment_text:
            description += f"\nКомментарий: {comment_text}"

        payload_parts = [
            f"uid={profile.telegram_id}",
            f"pid={profile.pk}",
            f"amt={amount_stars}",
            f"key={(idempotency_key or '')[:16]}",
            f"tok={uuid.uuid4().hex[:10]}",
            f"rid={rid[:12]}",
        ]
        payload = ";".join(payload_parts)
        if len(payload) > 120:
            payload = payload[:120]

        start_parameter = f"wallet_{profile.pk}"[:32]

        metadata_payload = {**(metadata or {})}
        log_extra = {
            "rid": rid,
            "request_id": rid,
            "telegram_user_id": profile.telegram_id,
            "profile_id": profile.pk,
            "amount": amount_stars,
            "has_comment": bool(comment_text),
            "idempotency_key": idempotency_key,
            "metadata_keys": sorted(metadata_payload.keys()),
            "build_fingerprint": get_build_fingerprint(),
        }
        logger.info("telegram invoice request", extra=log_extra)

        try:
            invoice_link = async_to_sync(self._create_invoice_link)(
                title=title,
                description=description,
                payload=payload,
                amount=amount_stars,
            )
        except TelegramBadRequest as exc:
            description_lower = str(exc).lower()
            if "purchases_disabled" in description_lower:
                raise TelegramStarsInvoiceError(
                    "Telegram временно отключил покупки Stars для вашего аккаунта.",
                    code="purchases_disabled",
                    details={"block_purchases": True},
                ) from exc
            if "user_not_found" in description_lower:
                raise TelegramStarsInvoiceError(
                    "Telegram не смог найти ваш аккаунт для оплаты Stars.",
                    code="user_not_found",
                    details={"block_purchases": True},
                ) from exc
            raise TelegramStarsInvoiceError(str(exc), code="telegram_error") from exc
        except Exception as exc:  # pragma: no cover - safety net
            raise TelegramStarsInvoiceError(str(exc), code="unknown_error") from exc

        logger.info(
            "telegram invoice success",
            extra={
                **log_extra,
                "invoice_link_preview": invoice_link[:32],
            },
        )

        return TelegramInvoiceResult(
            invoice_link=invoice_link,
            payload=payload,
            title=title,
            description=description,
            start_parameter=start_parameter,
        )


__all__ = [
    "TelegramStarsInvoiceService",
    "TelegramStarsInvoiceError",
    "TelegramInvoiceResult",
]