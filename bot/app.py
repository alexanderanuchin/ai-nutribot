import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.menu import router as menu_router
from handlers.profile_wizard import router as wizard_router
from services.backend import BackendClient
from middlewares.store import StoreMiddleware

def _clean_backend_url(raw: str) -> str:
    raw = (raw or "").rstrip("/")
    return raw[:-4] if raw.endswith("/api") else raw

def _is_https(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://")

class Config:
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
    bot_key = os.getenv("BOT_KEY") or os.getenv("BOT_INTERNAL_KEY") or "super-secret-bot-key"
    backend_url = _clean_backend_url(os.getenv("BACKEND_URL") or os.getenv("API_BASE") or "http://backend:8000")
    # По-умолчанию на ваш Vite dev-сервер
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:5173/")

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s:%(name)s:%(message)s")
    logging.getLogger("aiogram.event").setLevel(logging.INFO)

    cfg = Config()
    if not cfg.token:
        raise RuntimeError("BOT_TOKEN is not set")

    if not _is_https(cfg.webapp_url):
        logging.warning("WEBAPP_URL='%s' не HTTPS — кнопка WebApp будет скрыта, используем обычную ссылку.", cfg.webapp_url)

    bot = Bot(cfg.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    store = BackendClient(cfg.backend_url, cfg.bot_key)
    dp.update.middleware(StoreMiddleware(store, cfg.webapp_url))

    dp.include_router(menu_router)
    dp.include_router(wizard_router)

    await bot.set_my_commands([BotCommand(command="start", description="Запуск и меню")])

    logging.info("Bot started in POLLING mode")
    try:
        await dp.start_polling(bot)
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(main())
