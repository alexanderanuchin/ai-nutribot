"""Shared bot-level constants."""
from __future__ import annotations

from typing import Tuple

# Default quick top-up amounts for Telegram Stars (XTR)
TOPUP_AMOUNTS: Tuple[int, ...] = (100, 200, 500)

# Shared UX text for regions where Telegram blocks Stars purchases
STARS_BLOCKED_MESSAGE: str = (
    "Telegram временно отключил покупки Stars для вашего аккаунта. Откройте WebApp или напишите в поддержку."
)
