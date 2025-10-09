from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey, BaseStorage


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
        data["access_token"] = access_token

        return await handler(event, data)