from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from nutribot.middleware import get_request_id

from ..models import Profile, StarsRevenueSnapshot
from ..mtproto import TelegramMTProtoClient

logger = logging.getLogger("service.telegram.stars.metrics")


@dataclass(slots=True)
class StarsMetricsResult:
    snapshot: StarsRevenueSnapshot
    rate_rub: Decimal


class StarsMetricsService:
    def __init__(self, client: TelegramMTProtoClient) -> None:
        self.client = client

    def sync(self) -> StarsMetricsResult:
        rid = get_request_id()
        logger.info("stars metrics sync start", extra={"rid": rid, "request_id": rid})

        stats = self.client.get_stars_revenue_stats()
        rate = self._compute_rate(stats)
        payload = {
            "total_stars": int(stats.total_stars),
            "revenue_rub": str(stats.revenue_rub),
            "currency": stats.currency,
            "raw": stats.raw,
        }

        rate_rounded = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if rate > 0 else Decimal("0.00")

        with transaction.atomic():
            snapshot = StarsRevenueSnapshot.objects.create(
                stars_total=int(stats.total_stars),
                revenue_rub=stats.revenue_rub,
                currency=stats.currency or "RUB",
                rate_rub=rate_rounded,
                payload=payload,
            )
            Profile.objects.all().update(
                telegram_stars_rate_rub=rate_rounded,
                updated_at=timezone.now(),
            )

        logger.info(
            "stars metrics sync done",
            extra={
                "rid": rid,
                "request_id": rid,
                "rate": str(rate),
                "total_stars": stats.total_stars,
            },
        )
        return StarsMetricsResult(snapshot=snapshot, rate_rub=rate_rounded)

    def _compute_rate(self, stats) -> Decimal:
        if not stats.total_stars:
            return Decimal("0")
        rate = stats.revenue_rub / Decimal(stats.total_stars)
        return rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


__all__ = ["StarsMetricsService", "StarsMetricsResult"]