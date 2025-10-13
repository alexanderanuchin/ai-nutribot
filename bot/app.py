import asyncio
import logging
import os
import sys
from datetime import timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import Redis, RedisStorage
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
from bot.config import Config
from bot.handlers.menu import router as menu_router
from bot.handlers.plan import router as plan_router
from bot.handlers.profile_wizard import router as wizard_router
from bot.handlers.support import router as support_router
from bot.handlers.wallet import router as wallet_router
from bot.handlers.webapp_data import router as webapp_router
from bot.logging_utils import JsonLogFormatter, RequestIdFilter
from bot.middlewares.access_token import AccessTokenMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.store import StoreMiddleware


def _is_https(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://")


def _setup_logging() -> None:
    level_name = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    as_json = os.getenv("BOT_LOG_JSON", "0") == "1"

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(RequestIdFilter())
    if as_json:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s rid=%(request_id)s %(name)s: %(message)s"
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    logging.getLogger("aiogram.event").setLevel(level)


async def main() -> None:
    _setup_logging()

    cfg = Config.load()
    if not cfg.token:
        raise RuntimeError("BOT_TOKEN is not set")

    if not _is_https(cfg.webapp_url):
        logging.warning("WEBAPP_URL='%s' не HTTPS — кнопка WebApp будет скрыта, используем обычную ссылку.",
                        cfg.webapp_url)

    if cfg.backend_base_url.startswith(("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1")):
        logging.error(
            "BACKEND_URL='%s' недостижим из контейнера бота. "
            "Укажите адрес сервиса backend (например, http://backend:8000).",
            cfg.backend_base_url,
        )

    bot = Bot(cfg.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    redis = Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    storage = RedisStorage(redis=redis, data_ttl=timedelta(hours=1))
    dp = Dispatcher(storage=storage)

    backend = BackendClient(cfg.backend_base_url, bot_key=cfg.bot_key)
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(StoreMiddleware(backend, cfg.webapp_url, admin_ids=cfg.admin_ids))
    dp.update.middleware(AccessTokenMiddleware(dp.storage))

    dp.include_router(webapp_router)
    dp.include_router(menu_router)
    dp.include_router(plan_router)
    dp.include_router(wizard_router)
    dp.include_router(support_router)
    dp.include_router(wallet_router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="profile", description="Анкета профиля"),
            BotCommand(command="plan", description="Новый план питания"),
            BotCommand(command="history", description="История планов"),
            BotCommand(command="cancel", description="Отмена"),
            BotCommand(command="wallet", description="Баланс Stars"),
            BotCommand(command="terms", description="Условия покупки"),
            BotCommand(command="support", description="Поддержка"),
            BotCommand(command="paysupport", description="Оплата — помощь"),
        ]
    )

    logging.info("Bot started in POLLING mode")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=("message", "callback_query", "pre_checkout_query"),
        )
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
