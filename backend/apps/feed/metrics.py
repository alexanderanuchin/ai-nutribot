from __future__ import annotations

from typing import Any, Iterable

# Храним типы как Any, чтобы mypy не ругался на вызовы конструкторов в строгом режиме,
# когда prometheus_client отсутствует и подменяется no-op реализациями.
_CounterType: Any
_HistogramType: Any

try:  # pragma: no cover - import fallback
    from prometheus_client import Counter as _PrometheusCounter
    from prometheus_client import Histogram as _PrometheusHistogram
    _CounterType = _PrometheusCounter
    _HistogramType = _PrometheusHistogram
except ImportError:  # pragma: no cover - fallback when prometheus not installed
    class _NoopMetric:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":
            return self

        def observe(self, value: float) -> None:
            return None

        def inc(self, amount: int | float = 1) -> None:
            return None

    class _FallbackCounter(_NoopMetric):
        pass

    class _FallbackHistogram(_NoopMetric):
        pass

    _CounterType = _FallbackCounter
    _HistogramType = _FallbackHistogram


FEED_INGESTION_DURATION = _HistogramType(
    "feed_ingestion_duration_seconds",
    "Duration of feed ingestion runs in seconds.",
)
FEED_INGESTION_RUNS = _CounterType(
    "feed_ingestion_runs_total",
    "Number of feed ingestion runs partitioned by status.",
    ["status"],
)
FEED_INGESTION_ITEMS = _CounterType(
    "feed_ingestion_items_total",
    "Number of feed items processed during ingestion grouped by result type.",
    ["result"],
)
FEED_INGESTION_SOURCE_FAILURES = _CounterType(
    "feed_ingestion_source_failures_total",
    "Number of feed ingestion source failures partitioned by source name.",
    ["source"],
)


def _iter_failed_sources(values: Any) -> Iterable[str]:
    if not values:
        return []
    if isinstance(values, (list, tuple, set)):
        return [str(value) for value in values]
    return [str(values)]


def record_ingestion_metrics(*, result: dict[str, Any], duration_seconds: float) -> None:
    """Push counters/histograms for a completed ingestion run."""

    FEED_INGESTION_DURATION.observe(duration_seconds)

    status = "failure" if result.get("failed_sources") else "success"
    FEED_INGESTION_RUNS.labels(status=status).inc()

    for key in ("processed", "created", "updated", "skipped"):
        value = int(result.get(key, 0) or 0)
        if value:
            FEED_INGESTION_ITEMS.labels(result=key).inc(value)

    for source in _iter_failed_sources(result.get("failed_sources")):
        FEED_INGESTION_SOURCE_FAILURES.labels(source=str(source)).inc()


__all__ = [
    "FEED_INGESTION_DURATION",
    "FEED_INGESTION_RUNS",
    "FEED_INGESTION_ITEMS",
    "FEED_INGESTION_SOURCE_FAILURES",
    "record_ingestion_metrics",
]
