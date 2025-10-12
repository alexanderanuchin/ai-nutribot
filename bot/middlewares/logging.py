from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import BaseMiddleware

from bot.logging_utils import generate_request_id, reset_request_id, set_request_id


class LoggingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger("audit.telegram")

    async def __call__(self, handler, event: Any, data: dict[str, Any]):
        rid = self._extract_rid(event, data) or generate_request_id()
        token = set_request_id(rid)
        data["request_id"] = rid
        update_id = self._extract_update_id(event, data)
        from_user = data.get("event_from_user")
        chat = data.get("event_chat")
        event_type = type(event).__name__
        backend_client = data.get("backend")
        extra = {
            "update_id": update_id,
            "from_user": getattr(from_user, "id", None),
            "chat_id": getattr(chat, "id", None),
            "event_type": event_type,
        }
        await self._emit_monitoring(
            backend_client,
            level="INFO",
            message="bot update received",
            rid=rid,
            extra=extra,
        )
        try:
            self.logger.info(
                "bot update received rid=%s update_id=%s from_user=%s chat_id=%s event_type=%s",
                rid,
                update_id,
                getattr(from_user, "id", None),
                getattr(chat, "id", None),
                event_type,
            )
            return await handler(event, data)
        except Exception as exc:
            await self._emit_monitoring(
                backend_client,
                level="ERROR",
                message="bot update failed",
                rid=rid,
                extra={**extra, "error": str(exc)},
            )
            raise
        finally:
            reset_request_id(token)

    def _extract_update_id(self, event: Any, data: dict[str, Any]) -> Any:
        update = data.get("event_update")
        if update is not None:
            return getattr(update, "update_id", None)
        return getattr(event, "update_id", None)

    def _extract_rid(self, event: Any, data: dict[str, Any]) -> str | None:
        update = data.get("event_update")
        if update is not None:
            rid = self._extract_from_update(update)
            if rid:
                return rid
        return self._extract_from_update(event)

    def _extract_from_update(self, update: Any) -> str | None:
        if update is None:
            return None
        message = getattr(update, "message", None)
        if message is not None:
            rid = self._extract_from_message(message)
            if rid:
                return rid
        callback = getattr(update, "callback_query", None)
        if callback is not None:
            try:
                payload = json.loads(callback.data or "{}") if callback.data else {}
            except (TypeError, ValueError):
                payload = {}
            rid = payload.get("rid") if isinstance(payload, dict) else None
            if rid:
                return str(rid)
            if callback.message:
                return self._extract_from_message(callback.message)
        pre_checkout = getattr(update, "pre_checkout_query", None)
        if pre_checkout is not None:
            rid = self._extract_from_invoice_payload(pre_checkout.invoice_payload)
            if rid:
                return rid
        return None

    def _extract_from_message(self, message: Any) -> str | None:
        web_app_data = getattr(message, "web_app_data", None)
        if web_app_data and getattr(web_app_data, "data", None):
            try:
                payload = json.loads(web_app_data.data)
            except (TypeError, ValueError):
                payload = {}
            if isinstance(payload, dict):
                rid = payload.get("rid")
                if rid:
                    return str(rid)
        successful_payment = getattr(message, "successful_payment", None)
        if successful_payment:
            rid = self._extract_from_invoice_payload(successful_payment.invoice_payload)
            if rid:
                return rid
        return None

    def _extract_from_invoice_payload(self, payload: str | None) -> str | None:
        if not payload:
            return None
        parts = [chunk.strip() for chunk in payload.split(";") if chunk.strip()]
        for part in parts:
            if part.startswith("rid="):
                return part.split("=", 1)[1]
        return None

    async def _emit_monitoring(
            self,
            backend: Any,
            *,
            level: str,
            message: str,
            rid: str,
            extra: dict[str, Any] | None = None,
    ) -> None:
        sender = getattr(backend, "send_application_log", None)
        if not callable(sender):
            return
        try:
            await sender(
                level=level,
                message=message,
                request_id=rid,
                logger="bot.update",
                extra=extra,
            )
        except Exception:  # pragma: no cover - logging fallback
            self.logger.debug("failed to push monitoring log rid=%s", rid, exc_info=True)


__all__ = ["LoggingMiddleware"]
