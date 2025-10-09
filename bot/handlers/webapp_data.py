from __future__ import annotations

import json
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router()


@router.message(F.web_app_data)
async def webapp_auth_handler(message: Message, state: FSMContext) -> None:
    data = getattr(message.web_app_data, "data", None)
    if not data:
        await message.answer(
            "Получены пустые данные из WebApp. Откройте кабинет и попробуйте авторизоваться ещё раз."
        )
        return

    try:
        payload = json.loads(data)
    except (TypeError, ValueError):
        await message.answer(
            "Не удалось прочитать данные WebApp. Переоткройте экран и повторите попытку."
        )
        return

    if payload.get("type") != "auth":
        return

    access_token = payload.get("access_token")
    if not access_token:
        await message.answer(
            "WebApp не передал токен авторизации. Запустите кабинет заново и подтвердите вход."
        )
        return

    webapp_user_id = payload.get("user_id")
    from_user_id = getattr(message.from_user, "id", None)
    if webapp_user_id and from_user_id and int(webapp_user_id) != int(from_user_id):
        await message.answer(
            "WebApp передал сессию другого пользователя. Закройте экран и откройте его заново."
        )
        return

    await state.update_data(
        access_token=access_token,
        session_user_id=webapp_user_id or from_user_id,
        session_obtained_at=datetime.now(timezone.utc).isoformat(),
    )
    await message.answer(
        "Авторизация WebApp подтверждена. Можно продолжить операции с кошельком в боте."
    )