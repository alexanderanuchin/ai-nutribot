from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence

import httpx
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Case, F, IntegerField, Sum, Value, When
from django.utils import timezone

from nutribot.middleware import get_request_id

from ..models import TelegramStarLedgerEntry
from ..mtproto import StarsTransaction, TelegramMTProtoClient
from .stars import get_bot_star_balance

logger = logging.getLogger("service.telegram.stars.reconcile")


@dataclass(slots=True)
class LedgerMismatch:
    charge_id: str
    stars_transaction: StarsTransaction | None
    ledger_entry: TelegramStarLedgerEntry | None
    reason: str


@dataclass(slots=True)
class ReconciliationSummary:
    remote_balance: int
    ledger_balance: int
    bot_balance: int
    mismatches: List[LedgerMismatch]
    checked_transactions: int
    generated_at: timezone.datetime

    @property
    def has_discrepancies(self) -> bool:
        return bool(self.mismatches or self.remote_balance != self.ledger_balance)


class StarsReconciliationService:
    def __init__(self, client: TelegramMTProtoClient) -> None:
        self.client = client

    def reconcile(self, *, limit: int = 200) -> ReconciliationSummary:
        rid = get_request_id()
        logger.info("stars reconcile start", extra={"rid": rid, "request_id": rid, "limit": limit})

        status = self.client.get_stars_transactions(limit=limit)
        remote_balance = int(status.balance)
        remote_map = {
            tx.transaction_id: tx for tx in status.transactions if tx.transaction_id
        }

        ledger_entries = list(
            TelegramStarLedgerEntry.objects.filter(
                telegram_payment_charge_id__isnull=False
            )
            .select_related("profile", "wallet_transaction")
            .order_by("-occurred_at")[:limit]
        )
        ledger_map = {
            entry.telegram_payment_charge_id: entry for entry in ledger_entries if entry.telegram_payment_charge_id
        }

        ledger_balance = _aggregate_ledger_balance()
        bot_balance = get_bot_star_balance().amount

        mismatches: list[LedgerMismatch] = []

        for charge_id, tx in remote_map.items():
            entry = ledger_map.get(charge_id)
            if entry is None:
                mismatches.append(
                    LedgerMismatch(
                        charge_id=charge_id,
                        stars_transaction=tx,
                        ledger_entry=None,
                        reason="missing_in_ledger",
                    )
                )
                continue
            if int(entry.amount) != int(tx.stars):
                mismatches.append(
                    LedgerMismatch(
                        charge_id=charge_id,
                        stars_transaction=tx,
                        ledger_entry=entry,
                        reason="amount_mismatch",
                    )
                )

        for charge_id, entry in ledger_map.items():
            if charge_id not in remote_map:
                mismatches.append(
                    LedgerMismatch(
                        charge_id=charge_id,
                        stars_transaction=None,
                        ledger_entry=entry,
                        reason="missing_in_remote",
                    )
                )

        summary = ReconciliationSummary(
            remote_balance=remote_balance,
            ledger_balance=ledger_balance,
            bot_balance=bot_balance,
            mismatches=mismatches,
            checked_transactions=len(remote_map),
            generated_at=timezone.now(),
        )
        logger.info(
            "stars reconcile result",
            extra={
                "rid": rid,
                "request_id": rid,
                "remote_balance": remote_balance,
                "ledger_balance": ledger_balance,
                "bot_balance": bot_balance,
                "mismatch_count": len(mismatches),
            },
        )
        if summary.has_discrepancies:
            self._notify(summary, rid=rid)
        return summary

    def _notify(self, summary: ReconciliationSummary, *, rid: str) -> None:
        subject = "[NutriBot] Stars reconciliation detected discrepancies"
        lines = [
            f"Remote balance: {summary.remote_balance}",
            f"Ledger balance: {summary.ledger_balance}",
            f"Bot API balance: {summary.bot_balance}",
            f"Mismatches: {len(summary.mismatches)}",
            "",
        ]
        for mismatch in summary.mismatches:
            tx = mismatch.stars_transaction
            entry = mismatch.ledger_entry
            lines.append(
                " - "
                + mismatch.reason
                + f" | charge={mismatch.charge_id}"
                + (f" | stars={tx.stars}" if tx else "")
                + (f" | ledger_amount={entry.amount}" if entry else "")
                + (f" | profile={entry.profile_id}" if entry and entry.profile_id else "")
            )
        body = "\n".join(lines)

        logger.warning(
            "stars reconcile discrepancy",
            extra={
                "rid": rid,
                "request_id": rid,
                "remote_balance": summary.remote_balance,
                "ledger_balance": summary.ledger_balance,
                "bot_balance": summary.bot_balance,
                "mismatch_count": len(summary.mismatches),
            },
        )

        recipients: Sequence[str] = getattr(settings, "STARS_RECONCILE_EMAILS", ())
        if recipients:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=True,
            )

        webhook = getattr(settings, "SLACK_STARS_ALERT_WEBHOOK", "")
        if webhook:
            payload = {
                "text": subject,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Stars reconciliation mismatch*\n```\n{body}\n```",
                        },
                    }
                ],
            }
            try:
                with httpx.Client(timeout=5) as client:
                    client.post(webhook, json=payload)
            except httpx.HTTPError:  # pragma: no cover - network failure
                logger.exception("Failed to send Slack notification", extra={"rid": rid, "request_id": rid})


def _aggregate_ledger_balance() -> int:
    aggregate = TelegramStarLedgerEntry.objects.aggregate(
        total=Sum(
            Case(
                When(direction=TelegramStarLedgerEntry.Direction.CREDIT, then=F("amount")),
                When(direction=TelegramStarLedgerEntry.Direction.DEBIT, then=-F("amount")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    )
    return int(aggregate.get("total") or 0)


__all__ = [
    "ReconciliationSummary",
    "StarsReconciliationService",
]