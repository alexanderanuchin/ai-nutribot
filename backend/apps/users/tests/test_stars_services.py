from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.users.models import StarsRevenueSnapshot
from apps.users.mtproto import StarsRevenueStats
from apps.users.services.stars_metrics import StarsMetricsService


class DummyMTProtoClient:
    def __init__(self, stats: StarsRevenueStats) -> None:
        self._stats = stats

    def get_stars_revenue_stats(self) -> StarsRevenueStats:
        return self._stats


@pytest.mark.django_db
def test_stars_metrics_updates_snapshot_and_profiles() -> None:
    user_model = get_user_model()
    first_user = user_model.objects.create_user(username="metrics-1")
    second_user = user_model.objects.create_user(username="metrics-2")

    stats = StarsRevenueStats(
        total_stars=1200,
        revenue_rub=Decimal("3456.00"),
        currency="RUB",
        raw={"total_revenue_rub": "3456.00"},
    )

    service = StarsMetricsService(DummyMTProtoClient(stats))
    result = service.sync()

    assert result.rate_rub == Decimal("2.88")
    snapshot = StarsRevenueSnapshot.objects.get(pk=result.snapshot.pk)
    assert snapshot.stars_total == 1200
    assert snapshot.revenue_rub == Decimal("3456.00")
    assert snapshot.currency == "RUB"
    assert snapshot.payload["total_stars"] == 1200

    first_user.profile.refresh_from_db()
    second_user.profile.refresh_from_db()
    assert first_user.profile.telegram_stars_rate_rub == Decimal("2.88")
    assert second_user.profile.telegram_stars_rate_rub == Decimal("2.88")


@pytest.mark.django_db
def test_stars_metrics_handles_zero_volume() -> None:
    user_model = get_user_model()
    profile = user_model.objects.create_user(username="metrics-zero").profile
    profile.telegram_stars_rate_rub = Decimal("5.00")
    profile.save(update_fields=["telegram_stars_rate_rub"])

    stats = StarsRevenueStats(
        total_stars=0,
        revenue_rub=Decimal("0"),
        currency="RUB",
        raw={},
    )

    service = StarsMetricsService(DummyMTProtoClient(stats))
    result = service.sync()

    assert result.rate_rub == Decimal("0.00")
    profile.refresh_from_db()
    assert profile.telegram_stars_rate_rub == Decimal("0.00")
    snapshot = StarsRevenueSnapshot.objects.get(pk=result.snapshot.pk)
    assert snapshot.rate_rub == Decimal("0.00")