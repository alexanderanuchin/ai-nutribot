from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from datetime import timedelta
from urllib.parse import urlparse

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.redis import Redis, RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

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
from bot.services.bridge import BridgePublisher
from bot.services.commands import set_chat_menu_button, set_my_commands


async def _start_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    try:
        # Let aiogram derive allowed_updates from registered handlers so Web App
        # service payloads (e.g., web_app_data) are not filtered out.
        await dispatcher.start_polling(bot)
    finally:
        dispatcher.stop_polling()


def _is_https_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


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
    webhook_runner: web.AppRunner | None = None
    use_webhook = cfg.webhook_enable
    webhook_path = cfg.webhook_path if cfg.webhook_path.startswith("/") else f"/{cfg.webhook_path}"
    allowed_updates = dispatcher.resolve_used_update_types()
    if cfg.webhook_enable and not _is_https_url(cfg.webhook_url):
        logger.error(
            "Webhook URL must be HTTPS; falling back to polling",
            extra={
                "rid": get_request_id(),
                "webhook_url": cfg.webhook_url,
                "webhook_path": webhook_path,
                "webhook_port": cfg.webhook_port,
                "allowed_updates": allowed_updates,
            },
        )
        use_webhook = False

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
    polling_task: asyncio.Task[None] | None = None
    if use_webhook:
        webhook_secret = cfg.webhook_secret or None
        webhook_handler = SimpleRequestHandler(dispatcher, bot, secret_token=webhook_secret)
        app = web.Application()

        @web.middleware
        async def reqlog_mw(request: web.Request, handler):
            rid = getattr(request, "request_id", get_request_id())
            if request.path == webhook_path:
                hdr = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
                logger.info(
                    "webhook request",
                    extra={
                        "rid": rid,
                        "path": request.path,
                        "method": request.method,
                        "has_secret": bool(hdr),
                        "remote": request.remote,
                        "ua": request.headers.get("User-Agent"),
                        "content_length": request.headers.get("Content-Length"),
                    },
                )
            return await handler(request)

        async def health(_req: web.Request):
            return web.Response(text="ok")

        app.middlewares.append(reqlog_mw)
        app.router.add_get("/healthz", health)
        webhook_handler.register(app, path=webhook_path)
        setup_application(app, dispatcher, bot=bot)

        webhook_runner = web.AppRunner(app)
        try:
            await webhook_runner.setup()
            site = web.TCPSite(webhook_runner, host="0.0.0.0", port=cfg.webhook_port)
            await bot.set_webhook(
                url=cfg.webhook_url,
                secret_token=webhook_secret,
                drop_pending_updates=True,
                allowed_updates=allowed_updates,
            )
            await site.start()
            logger.info(
                "Bot started in WEBHOOK mode",
                extra={
                    "rid": get_request_id(),
                    "webhook_url": cfg.webhook_url,
                    "webhook_path": webhook_path,
                    "webhook_port": cfg.webhook_port,
                    "allowed_updates": allowed_updates,
                },
            )
        except TelegramBadRequest as exc:
            logger.error(
                "Telegram rejected webhook; switching to polling",
                extra={
                    "rid": get_request_id(),
                    "error": str(exc),
                    "webhook_url": cfg.webhook_url,
                    "webhook_path": webhook_path,
                    "webhook_port": cfg.webhook_port,
                    "allowed_updates": allowed_updates,
                },
            )
            use_webhook = False
            with suppress(Exception):
                await bot.delete_webhook(drop_pending_updates=False)
            if webhook_runner:
                with suppress(Exception):
                    await webhook_runner.cleanup()
                webhook_runner = None

    if not use_webhook:
        polling_task = asyncio.create_task(_start_polling(bot, dispatcher), name="aiogram-polling")
        polling_task.add_done_callback(lambda _: stop_event.set())
        logger.info("Bot started in POLLING mode", extra={"rid": get_request_id()})

    try:
        await stop_event.wait()
    finally:
        if polling_task and not polling_task.done():
            polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await polling_task
        if webhook_runner:
            await bot.delete_webhook(drop_pending_updates=False)
            await webhook_runner.cleanup()
        await dispatcher.storage.close()
        await dispatcher.storage.wait_closed()
        await bridge_publisher.close()
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
