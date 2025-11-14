from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent, Message

from bot.logkit import get_request_id
from bot.utils.texts import ERROR_TEXT

logger = logging.getLogger("bot.errors")


def _extract_message(event: ErrorEvent) -> Message | None:
    update = event.update
    if update is None:
        return None
    message = getattr(update, "message", None)
    if message is not None:
        return message
    callback = getattr(update, "callback_query", None)
    if callback and callback.message:
        return callback.message
    return None


async def error_handler(event: ErrorEvent) -> None:
    exc = event.exception
    rid = get_request_id()
    logger.exception(
        "bot update error",
        extra={
            "rid": rid,
            "exception": repr(exc),
        },
    )
    message = _extract_message(event)
    if message is None:
        return
    try:
        await message.answer(ERROR_TEXT)
    except TelegramAPIError:
        logger.debug("failed to notify user about error", extra={"rid": rid})
    except Exception:  # pragma: no cover - fallback
        logger.debug("unexpected error while notifying user", extra={"rid": rid}, exc_info=True)


def register_error_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.errors.register(error_handler)


__all__ = ["register_error_handlers"]