from __future__ import annotations

import os
import sys
from typing import Final

import httpx

from bot.config import _DEF_BACKEND, _DEF_API_KEYS, _clean_backend_url

_DEFAULT_TIMEOUT: Final[float] = float(os.getenv("BOT_HEALTHCHECK_TIMEOUT", "5"))


def _resolve_health_url() -> str:
    explicit = os.getenv("BOT_HEALTHCHECK_URL")
    if explicit:
        return explicit

    for key in _DEF_API_KEYS:
        candidate = os.getenv(key)
        if candidate:
            base = _clean_backend_url(candidate)
            break
    else:
        base = _DEF_BACKEND

    if base.endswith("/metrics") or base.endswith("/healthz"):
        return base
    return f"{base}/metrics"


def main() -> int:
    url = _resolve_health_url()
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
            response = client.get(url)
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - propagate failure details
        print(f"bot.healthcheck: failed to reach {url}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
