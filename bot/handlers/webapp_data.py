from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.logging_utils import get_request_id, mask_token

from .wallet import MAX_TOPUP_AMOUNT, MIN_TOPUP_AMOUNT, build_stars_topup_invoice

router = Router()
logger = logging.getLogger("audit.telegram")


async def _handle_auth_payload(message: Message, state: FSMContext, payload: dict) -> None:
    access_token = payload.get("access_token")
    if not access_token:
        await message.answer(
            "WebApp не передал токен авторизации. Запустите кабинет заново и подтвердите вход."
        )
        logger.warning(
            "webapp auth missing_token rid=%s from_user=%s",
            get_request_id(),
            getattr(message.from_user, "id", None),
        )
        return

    webapp_user_id = payload.get("user_id")
    from_user_id = getattr(message.from_user, "id", None)
    if webapp_user_id and from_user_id and int(webapp_user_id) != int(from_user_id):
        await message.answer(
            "WebApp передал сессию другого пользователя. Закройте экран и откройте его заново."
        )
        logger.warning(
            "webapp auth user_mismatch rid=%s payload_user=%s telegram_user=%s",
            get_request_id(),
            webapp_user_id,
            from_user_id,
        )
        return

    refresh_token = payload.get("refresh_token") or payload.get("refresh")
    expires_at = payload.get("expires_at") or payload.get("exp")

    updates = {
        "access_token": access_token,
        "session_user_id": webapp_user_id or from_user_id,
        "session_obtained_at": datetime.now(timezone.utc).isoformat(),
    }
    if refresh_token:
        updates["refresh_token"] = refresh_token
    if expires_at:
        updates["session_expires_at"] = expires_at

    logger.info(
        "webapp auth_success rid=%s telegram_user_id=%s access=%s refresh=%s expires_at=%s",
        get_request_id(),
        webapp_user_id or from_user_id,
        mask_token(access_token),
        mask_token(refresh_token),
        expires_at,
    )
    await state.update_data(**updates)
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
        logger.warning("webapp topup missing_user rid=%s", get_request_id())
        return

    raw_amount = payload.get("amount")
    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        await message.answer("WebApp передал некорректную сумму для пополнения.")
        logger.warning("webapp topup invalid_amount rid=%s amount=%s", get_request_id(), raw_amount)
        return

    if amount < MIN_TOPUP_AMOUNT:
        await message.answer(
            "Сумма пополнения слишком мала. Минимум — " f"{MIN_TOPUP_AMOUNT} XTR."
        )
        logger.warning(
            "webapp topup below_min rid=%s amount=%s min=%s",
            get_request_id(),
            amount,
            MIN_TOPUP_AMOUNT,
        )
        return

    if amount > MAX_TOPUP_AMOUNT:
        await message.answer(
            "Сумма пополнения слишком большая. Разделите платёж на несколько операций."
        )
        logger.warning(
            "webapp topup above_max rid=%s amount=%s max=%s",
            get_request_id(),
            amount,
            MAX_TOPUP_AMOUNT,
        )
        return

    state_data = await state.get_data()
    stored_token = state_data.get("access_token") or access_token
    session_user_id = state_data.get("session_user_id")

    if not stored_token:
        await message.answer(
            "Сначала авторизуйтесь через WebApp, чтобы пополнить баланс. "
            "Если экран был открыт давно, закройте его и авторизуйтесь заново."
        )
        logger.warning("webapp topup missing_token rid=%s", get_request_id())
        return

    if session_user_id is not None:
        try:
            if int(session_user_id) != int(message.from_user.id):
                await message.answer(
                    "Сессия WebApp принадлежит другому пользователю. Закройте экран и войдите снова."
                )
                logger.warning(
                    "webapp topup session_mismatch rid=%s stored=%s actual=%s",
                    get_request_id(),
                    session_user_id,
                    message.from_user.id,
                )
                return
        except (TypeError, ValueError):
            await message.answer(
                "Не удалось проверить пользователя WebApp. Закройте экран и авторизуйтесь заново."
            )
            logger.warning("webapp topup session_parse_error rid=%s", get_request_id())
            return

    comment = payload.get("comment")
    if state_data.get("stars_purchase_blocked"):
        await message.answer(
            "Пополнение Stars недоступно: Telegram временно отключил покупки в вашем регионе."
        )
        logger.info(
            "webapp topup blocked rid=%s telegram_user_id=%s", get_request_id(), getattr(message.from_user, "id", None)
        )
        return
    logger.info(
        "webapp topup_request rid=%s telegram_user_id=%s amount=%s has_comment=%s",
        get_request_id(),
        getattr(message.from_user, "id", None),
        amount,
        bool(comment),
    )
    invoice = build_stars_topup_invoice(
        message.from_user.id,
        amount,
        comment=comment,
        rid=get_request_id(),
    )
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
        logger.error("webapp state_missing rid=%s", get_request_id())
        return

    data = getattr(message.web_app_data, "data", None)
    if not data:
        await message.answer(
            "Получены пустые данные из WebApp. Откройте кабинет и попробуйте авторизоваться ещё раз."
        )
        logger.warning("webapp empty_payload rid=%s", get_request_id())
        return

    try:
        payload = json.loads(data)
    except (TypeError, ValueError):
        await message.answer(
            "Не удалось прочитать данные WebApp. Переоткройте экран и повторите попытку."
        )
        logger.warning("webapp decode_failed rid=%s", get_request_id())
        return

    payload_type = str(payload.get("type") or "").lower()
    action = str(payload.get("action") or "").lower()
    logger.info(
        "webapp payload rid=%s type=%s action=%s keys=%s",
        get_request_id(),
        payload_type,
        action,
        sorted(payload.keys()),
    )

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
    logger.warning(
        "webapp unknown_payload rid=%s keys=%s",
        get_request_id(),
        sorted(payload.keys()),
    )