from __future__ import annotations
import os
from datetime import datetime, timezone as dt_timezone
from typing import Optional

from django.utils import timezone
from zoneinfo import ZoneInfo

_MSK_TZ = ZoneInfo(os.environ.get("TIME_DEFAULT_TZ", "Europe/Moscow"))


def to_moscow(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    # делаем aware и приводим к МСК
    aware_dt = dt
    if timezone.is_naive(aware_dt):
        aware_dt = timezone.make_aware(aware_dt, dt_timezone.utc)
    return aware_dt.astimezone(_MSK_TZ)
