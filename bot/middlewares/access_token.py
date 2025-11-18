from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey, BaseStorage

from bot.backend_client import BackendClient


class AccessTokenMiddleware(BaseMiddleware):
    """Loads/stores access tokens in FSM storage for each Telegram user."""

    def __init__(self, storage: BaseStorage):
        super().__init__()
        self._storage = storage

    async def __call__(self, handler, event, data):
        state: FSMContext | None = data.get("state")
        bot = data.get("bot")
        from_user = getattr(event, "from_user", None)

        chat = getattr(event, "chat", None)
        if chat is None and hasattr(event, "message"):
            chat = getattr(event.message, "chat", None)

        if state is None and bot and from_user:
            key = StorageKey(
                bot_id=bot.id,
                user_id=from_user.id,
                chat_id=getattr(chat, "id", from_user.id),
            )
            state = FSMContext(storage=self._storage, key=key)
            data["state"] = state

        access_token = None
        if state is not None:
            stored = await state.get_data()
            access_token = stored.get("access_token")

        if not access_token and bot and from_user:
            backend: BackendClient | None = data.get("backend")
            if backend:
                session_data = await backend.get_telegram_session(from_user.id)
                if session_data:
                    access_token = session_data.get("access")
                    refresh = session_data.get("refresh")
                    expires_at = session_data.get("expires_at")
                    if access_token:
                        await state.update_data(
                            access_token=access_token,
                            refresh_token=refresh,
                            session_user_id=from_user.id,
                            session_expires_at=expires_at,
                        )
        data["access_token"] = access_token

        return await handler(event, data)