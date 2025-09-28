import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# NOTE:
# The bot can be executed both as a module (``python -m bot.app``)
# and as a script (``python bot/app.py``).  When executed as a script
# ``__package__`` is empty and the parent directory of the ``bot``
# package is not present in ``sys.path`` which breaks absolute imports.
# To make both execution methods work we ensure that the repository root
# is available on ``sys.path`` before importing package modules.
if __package__ in {None, ""}:
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

from bot.backend_client import BackendClient
from bot.handlers.menu import router as menu_router
from bot.handlers.plan import router as plan_router
from bot.handlers.profile_wizard import router as wizard_router
from bot.middlewares.access_token import AccessTokenMiddleware
from bot.middlewares.store import StoreMiddleware


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
        logging.warning("WEBAPP_URL='%s' не HTTPS — кнопка WebApp будет скрыта, используем обычную ссылку.",
                        cfg.webapp_url)

    bot = Bot(cfg.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    backend = BackendClient(cfg.backend_url)
    dp.update.middleware(StoreMiddleware(backend, cfg.webapp_url))
    dp.update.middleware(AccessTokenMiddleware(dp.storage))

    dp.include_router(menu_router)
    dp.include_router(plan_router)
    dp.include_router(wizard_router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="profile", description="Анкета профиля"),
            BotCommand(command="plan", description="Новый план питания"),
            BotCommand(command="history", description="История планов"),
            BotCommand(command="cancel", description="Отмена"),
        ]
    )


    logging.info("Bot started in POLLING mode")
    try:
        await dp.start_polling(bot)
    finally:
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
