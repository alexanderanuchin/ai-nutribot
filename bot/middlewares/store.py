from __future__ import annotations

from typing import Iterable, Tuple

from aiogram import BaseMiddleware


class StoreMiddleware(BaseMiddleware):
    def __init__(self, store, webapp_url: str, *, admin_ids: Iterable[int] | None = None):
        super().__init__()
        self.store = store
        self.webapp_url = webapp_url
        self.admin_ids: Tuple[int, ...] = tuple(admin_ids or ())

    async def __call__(self, handler, event, data):
        # кладём зависимости в data — aiogram передаст их по именам параметров хендлеров
        data["store"] = self.store
        data["backend"] = self.store
        data["backend_client"] = self.store
        data["webapp_url"] = self.webapp_url
        data["admin_ids"] = self.admin_ids
        return await handler(event, data)
