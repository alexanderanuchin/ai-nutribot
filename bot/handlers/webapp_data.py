from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.constants import STARS_BLOCKED_MESSAGE
from bot.logkit import get_request_id, mask_token

from .wallet import (
    MAX_TOPUP_AMOUNT,
    MIN_TOPUP_AMOUNT,
    build_stars_topup_invoice,
    plan_topup_payload,
)

router = Router()
logger = logging.getLogger("audit.telegram")


async def _handle_auth_payload(message: Message, state: FSMContext, payload: dict) -> None:
    rid = get_request_id()
    access_token = payload.get("access_token")
    if not access_token:
        await message.answer(
            "WebApp не передал токен авторизации. Запустите кабинет заново и подтвердите вход."
        )
        logger.warning(
            "webapp auth missing_token",
            extra={
                "rid": rid,
                "from_user": getattr(message.from_user, "id", None),
            },
        )
        return

    webapp_user_id = payload.get("user_id")
    from_user_id = getattr(message.from_user, "id", None)
    if webapp_user_id and from_user_id and int(webapp_user_id) != int(from_user_id):
        await message.answer(
            "WebApp передал сессию другого пользователя. Закройте экран и откройте его заново."
        )
        logger.warning(
            "webapp auth user_mismatch",
            extra={
                "rid": rid,
                "payload_user": webapp_user_id,
                "telegram_user": from_user_id,
            },
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
        "webapp auth_success",
        extra={
            "rid": rid,
            "telegram_user_id": webapp_user_id or from_user_id,
            "access": mask_token(access_token),
            "refresh": mask_token(refresh_token),
            "expires_at": expires_at,
        },
    )
    await state.update_data(**updates)
    await message.answer("Авторизация подтверждена ✅", reply_markup=ReplyKeyboardRemove())


async def _handle_topup_payload(
    message: Message,
    state: FSMContext,
    payload: dict,
    *,
    access_token: str | None,
    provider_token: str | None,
) -> None:
    rid = get_request_id()
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        logger.warning(
            "webapp topup missing_user",
            extra={"rid": rid},
        )
        return

    raw_amount = payload.get("amount")
    try:
        amount = int(raw_amount)
    except (TypeError, ValueError):
        await message.answer("WebApp передал некорректную сумму для пополнения.")
        logger.warning(
            "webapp topup invalid_amount",
            extra={"rid": rid, "amount": raw_amount},
        )
        return

    if amount < MIN_TOPUP_AMOUNT:
        await message.answer(
            "Сумма пополнения слишком мала. Минимум — " f"{MIN_TOPUP_AMOUNT} XTR."
        )
        logger.warning(
            "webapp topup below_min",
            extra={
                "rid": rid,
                "amount": amount,
                "min_amount": MIN_TOPUP_AMOUNT,
            },
        )
        return

    if amount > MAX_TOPUP_AMOUNT:
        await message.answer(
            "Сумма пополнения слишком большая. Разделите платёж на несколько операций."
        )
        logger.warning(
            "webapp topup above_max",
            extra={
                "rid": rid,
                "amount": amount,
                "max_amount": MAX_TOPUP_AMOUNT,
            },
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
        logger.warning(
            "webapp topup missing_token",
            extra={"rid": rid},
        )
        return

    if session_user_id is not None:
        try:
            if int(session_user_id) != int(message.from_user.id):
                await message.answer(
                    "Сессия WebApp принадлежит другому пользователю. Закройте экран и войдите снова."
                )
                logger.warning(
                    "webapp topup session_mismatch",
                    extra={
                        "rid": rid,
                        "stored_user_id": session_user_id,
                        "actual_user_id": message.from_user.id,
                    },
                )
                return
        except (TypeError, ValueError):
            await message.answer(
                "Не удалось проверить пользователя WebApp. Закройте экран и авторизуйтесь заново."
            )
            logger.warning(
                "webapp topup session_parse_error",
                extra={"rid": rid},
            )
            return

    comment = payload.get("comment")
    if state_data.get("stars_purchase_blocked"):
        await message.answer(
            STARS_BLOCKED_MESSAGE
        )
        logger.info(
            "webapp topup blocked",
            extra={
                "rid": rid,
                "telegram_user_id": getattr(message.from_user, "id", None),
            },
        )
        return
    logger.info(
        "webapp topup_request",
        extra={
            "rid": rid,
            "telegram_user_id": getattr(message.from_user, "id", None),
            "amount": amount,
            "has_comment": bool(comment),
        },
    )
    payload_extra = plan_topup_payload(state_data)
    invoice = build_stars_topup_invoice(
        message.from_user.id,
        amount,
        comment=comment,
        rid=rid,
        provider_token=provider_token,
        payload_extra=payload_extra,
    )
    await message.answer_invoice(**invoice)
    if payload_extra:
        pending = state_data.get("pending_action")
        if isinstance(pending, dict):
            await state.update_data(pending_action={**pending, "status": "invoice_sent"})


@router.message(F.web_app_data)
async def webapp_data_handler(
    message: Message,
    state: FSMContext,
    access_token: str | None,
    provider_token: str | None,
) -> None:
    rid = get_request_id()
    if state is None:
        await message.answer(
            "Не удалось получить состояние диалога. Закройте WebApp и откройте его заново."
        )
        logger.error(
            "webapp state_missing",
            extra={"rid": rid},
        )
        return

    data = getattr(message.web_app_data, "data", None)
    if not data:
        await message.answer(
            "Получены пустые данные из WebApp. Откройте кабинет и попробуйте авторизоваться ещё раз."
        )
        logger.warning(
            "webapp empty_payload",
            extra={"rid": rid},
        )
        return

    try:
        payload = json.loads(data)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        await message.answer(
            "Не удалось прочитать данные WebApp. Переоткройте экран и повторите попытку."
        )
        logger.warning(
            "webapp decode_failed",
            extra={"rid": rid, "error": str(exc)},
        )
        return

    payload_keys = sorted(payload.keys()) if isinstance(payload, dict) else []
    logger.info(
        "web_app_data received", extra={"rid": rid, "payload_keys": payload_keys}
    )

    payload_type = str(payload.get("type") or "").lower()
    action = str(payload.get("action") or "").lower()
    logger.info(
        "webapp payload",
        extra={
            "rid": rid,
            "type": payload_type,
            "action": action,
            "payload_keys": payload_keys,
        },
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
            provider_token=provider_token,
        )
        return

    await message.answer("Получено неизвестное действие из WebApp.")
    logger.warning(
        "webapp unknown_payload",
        extra={
            "rid": rid,
            "payload_keys": payload_keys,
        },
    )