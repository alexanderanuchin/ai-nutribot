from __future__ import annotations

from collections import Counter
from threading import Lock
from typing import Dict

from django.core.cache import cache

_METRIC_PREFIX = "auth:webapp_login_failure"
_local_counters: Counter[str] = Counter()
_lock = Lock()


def _cache_key(reason: str) -> str:
    return f"{_METRIC_PREFIX}:{reason}"


def increment_login_failure(reason: str) -> None:
    """Increment counters for WebApp login failures by reason."""

    normalized = reason or "unknown"
    with _lock:
        _local_counters[normalized] += 1

    key = _cache_key(normalized)
    try:
        added = cache.add(key, 0, timeout=None)
    except Exception:
        added = False
    try:
        if added:
            cache.incr(key, delta=0)
        cache.incr(key)
    except Exception:
        # Cache backend may not support incr; fall back to in-memory counter only.
        pass


def get_local_failure_counters() -> Dict[str, int]:
    """Return a snapshot of in-process counters for diagnostics."""

    with _lock:
        return dict(_local_counters)


__all__ = ["increment_login_failure", "get_local_failure_counters"]