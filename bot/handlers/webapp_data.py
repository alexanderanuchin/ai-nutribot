from __future__ import annotations

import json
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .wallet import build_stars_topup_invoice

router = Router()


async def _handle_auth_payload(message: Message, state: FSMContext, payload: dict) -> None:
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


async def _handle_topup_payload(
    message: Message,
    state: FSMContext,
    payload: dict,
    *,
    access_token: str | None,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    raw_amount = payload.get("amount")
    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        await message.answer("WebApp передал некорректную сумму для пополнения.")
        return

    if amount <= 0:
        await message.answer("Сумма пополнения должна быть положительным числом.")
        return

    state_data = await state.get_data()
    stored_token = state_data.get("access_token") or access_token
    session_user_id = state_data.get("session_user_id")

    if not stored_token:
        await message.answer(
            "Сначала авторизуйтесь через WebApp, чтобы пополнить баланс. "
            "Если экран был открыт давно, закройте его и авторизуйтесь заново."
        )
        return

    if session_user_id is not None:
        try:
            if int(session_user_id) != int(message.from_user.id):
                await message.answer(
                    "Сессия WebApp принадлежит другому пользователю. Закройте экран и войдите снова."
                )
                return
        except (TypeError, ValueError):
            await message.answer(
                "Не удалось проверить пользователя WebApp. Закройте экран и авторизуйтесь заново."
            )
            return

    comment = payload.get("comment")
    invoice = build_stars_topup_invoice(message.from_user.id, amount, comment=comment)
    await message.answer_invoice(**invoice)


@router.message(F.web_app_data)
async def webapp_data_handler(
    message: Message,
    state: FSMContext,
    access_token: str | None,
) -> None:
    if state is None:
        await message.answer(
            "Не удалось получить состояние диалога. Закройте WebApp и откройте его заново."
        )
        return

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

    payload_type = str(payload.get("type") or "").lower()
    action = str(payload.get("action") or "").lower()

    if payload_type == "auth" or action == "auth":
        await _handle_auth_payload(message, state, payload)
        return

    if payload_type in {"topup", "wallet_topup"} or action in {"topup", "wallet_topup"}:
        await _handle_topup_payload(
            message,
            state,
            payload,
            access_token=access_token,
        )
        return

    await message.answer("Получено неизвестное действие из WebApp.")
