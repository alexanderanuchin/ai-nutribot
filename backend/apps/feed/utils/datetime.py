from __future__ import annotations
import os
from django.utils import timezone
from zoneinfo import ZoneInfo

_MSK_TZ = ZoneInfo(os.environ.get("TIME_DEFAULT_TZ", "Europe/Moscow"))


def to_moscow(dt):
    if not dt:
        return None
    # делаем aware и приводим к МСК
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(_MSK_TZ)