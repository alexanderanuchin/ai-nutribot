from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import Redis, RedisStorage

from bot.backend_client import BackendClient
from bot.config import Config
from bot.logkit import configure_logging, get_request_id
from bot.middlewares.bridge import BridgeEventsMiddleware
from bot.middlewares.access_token import AccessTokenMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.store import StoreMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.routers.commands import router as commands_router
from bot.routers.errors import register_error_handlers
from bot.routers.menu import router as menu_router
from bot.handlers.plan import router as plan_router
from bot.handlers.profile_wizard import router as wizard_router
from bot.handlers.support import router as support_router
from bot.handlers.wallet import router as wallet_router
from bot.handlers.webapp_data import router as webapp_router
from bot.services.bridge import BridgePublisher
from bot.services.commands import set_chat_menu_button, set_my_commands

ALLOWED_UPDATES = ("message", "callback_query", "pre_checkout_query")


async def _start_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    try:
        await dispatcher.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        dispatcher.stop_polling()


async def main() -> None:
    configure_logging()
    cfg = Config.load()
    if not cfg.token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    logger = logging.getLogger("bot.main")
    if cfg.backend_base_url.startswith(("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1")):
        logger.error(
            "BACKEND_URL='%s' недостижим из контейнера бота. Укажите адрес сервиса backend (например, http://backend:8000).",
            cfg.backend_base_url,
        )

    bot = Bot(cfg.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    redis = Redis(host=cfg.redis_host, port=cfg.redis_port)
    storage = RedisStorage(redis=redis, data_ttl=timedelta(hours=cfg.session_ttl_hours))
    bridge_publisher = BridgePublisher(redis)
    dispatcher = Dispatcher(storage=storage)

    backend = BackendClient(cfg.backend_base_url, bot_key=cfg.bot_key)
    dispatcher.update.middleware(LoggingMiddleware())
    dispatcher.update.middleware(BridgeEventsMiddleware(bridge_publisher))
    dispatcher.update.middleware(StoreMiddleware(backend, cfg))
    dispatcher.update.middleware(
        ThrottleMiddleware(limit=cfg.throttle_limit, interval=cfg.throttle_interval)
    )
    dispatcher.update.middleware(AccessTokenMiddleware(dispatcher.storage))

    dispatcher.include_router(webapp_router)
    dispatcher.include_router(commands_router)
    dispatcher.include_router(menu_router)
    dispatcher.include_router(plan_router)
    dispatcher.include_router(wizard_router)
    dispatcher.include_router(support_router)
    dispatcher.include_router(wallet_router)

    register_error_handlers(dispatcher)
    await set_my_commands(bot)
    await set_chat_menu_button(bot, webapp_url=cfg.webapp_webview_url)

    stop_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Shutdown signal received", extra={"rid": get_request_id(), "signal": sig.name})
        stop_event.set()
        dispatcher.stop_polling()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:  # pragma: no cover - Windows
            pass

    polling_task = asyncio.create_task(_start_polling(bot, dispatcher), name="aiogram-polling")
    polling_task.add_done_callback(lambda _: stop_event.set())
    logger.info("Bot started in POLLING mode", extra={"rid": get_request_id()})

    try:
        await stop_event.wait()
    finally:
        if not polling_task.done():
            polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await polling_task
        await dispatcher.storage.close()
        await dispatcher.storage.wait_closed()
        await bridge_publisher.close()
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
