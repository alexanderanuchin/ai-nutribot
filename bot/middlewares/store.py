from __future__ import annotations

from typing import Tuple

from aiogram import BaseMiddleware

from bot.config import Config


class StoreMiddleware(BaseMiddleware):
    def __init__(self, store, config: Config) -> None:
        super().__init__()
        self.store = store
        self.config = config
        self.admin_ids: Tuple[int, ...] = tuple(config.admin_ids)
        self.bot_username = (config.bot_username or "").lstrip("@")

    async def __call__(self, handler, event, data):
        data["store"] = self.store
        data["backend"] = self.store
        data["backend_client"] = self.store
        data["config"] = self.config
        data["webapp_url"] = self.config.webapp_webview_url or self.config.webapp_url
        data["webapp_browser_url"] = self.config.webapp_browser_url
        data["admin_ids"] = self.admin_ids
        data["bot_username"] = self.bot_username
        data["privacy_url"] = self.config.privacy_url
        data["terms_url"] = self.config.terms_url
        data["support_url"] = self.config.support_url
        data["hero_image_url"] = self.config.hero_image_url
        data["experimental_menu"] = self.config.experimental_menu
        return await handler(event, data)
