from __future__ import annotations

from typing import Any, Iterable

try:  # pragma: no cover - import fallback
    from prometheus_client import Counter as _Counter
    from prometheus_client import Histogram as _Histogram
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

    class _Counter(_NoopMetric):
        pass

    class _Histogram(_NoopMetric):
        pass


FEED_INGESTION_DURATION = _Histogram(
    "feed_ingestion_duration_seconds",
    "Duration of feed ingestion runs in seconds.",
)
FEED_INGESTION_RUNS = _Counter(
    "feed_ingestion_runs_total",
    "Number of feed ingestion runs partitioned by status.",
    ["status"],
)
FEED_INGESTION_ITEMS = _Counter(
    "feed_ingestion_items_total",
    "Number of feed items processed during ingestion grouped by result type.",
    ["result"],
)
FEED_INGESTION_SOURCE_FAILURES = _Counter(
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
        FEED_INGESTION_SOURCE_FAILURES.labels(source=source).inc()


__all__ = [
    "FEED_INGESTION_DURATION",
    "FEED_INGESTION_RUNS",
    "FEED_INGESTION_ITEMS",
    "FEED_INGESTION_SOURCE_FAILURES",
    "record_ingestion_metrics",
]