from __future__ import annotations

from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey

from bot.backend_client import BackendClient


class AccessTokenMiddleware(BaseMiddleware):
    """
    Поднимает access_token для каждого Telegram-пользователя:

    - сначала пытается взять из FSM (Redis),
    - если нет — тянет из backend`а через /api/users/bot/telegram/session/<tg_id>/,
    - кладёт access_token в data["access_token"], чтобы им могли пользоваться хэндлеры.
    """

    def __init__(self, storage: BaseStorage) -> None:
        super().__init__()
        self._storage = storage

    async def __call__(self, handler, event: Any, data: dict[str, Any]):
        # В aiogram 3 "кто прислал апдейт" уже разложен в data
        state: FSMContext | None = data.get("state")
        bot = data.get("bot")
        from_user = data.get("event_from_user")
        chat = data.get("event_chat")

        # Если апдейт не от пользователя (service, my_chat_member и т.п.) — просто пропускаем
        if bot is None or from_user is None:
            return await handler(event, data)

        # 1. Гарантируем FSMContext для (bot_id, user_id, chat_id)
        if state is None:
            key = StorageKey(
                bot_id=bot.id,
                user_id=from_user.id,
                chat_id=getattr(chat, "id", from_user.id),
            )
            state = FSMContext(storage=self._storage, key=key)
            data["state"] = state

        # 2. Пробуем взять токен из FSM
        stored = await state.get_data()
        access_token: str | None = stored.get("access_token")

        # 3. Если токена нет в FSM — вытаскиваем из backend
        if not access_token:
            backend: BackendClient | None = data.get("backend")
            if backend is not None:
                session = await backend.get_telegram_session(from_user.id)
                if session:
                    access_token = session.get("access")
                    refresh = session.get("refresh")
                    expires_at = session.get("expires_at")
                    await state.update_data(
                        access_token=access_token,
                        refresh_token=refresh,
                        session_user_id=from_user.id,
                        session_expires_at=expires_at,
                    )

        # 4. Кладём access_token в data — его уже ждут wallet/profile/etc
        data["access_token"] = access_token
        return await handler(event, data)
