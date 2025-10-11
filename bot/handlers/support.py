from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

_TERMS_TEXT = (
    "<b>Условия покупки цифровых товаров</b>\n\n"
    "• Покупки совершаются в Telegram Stars (XTR) и относятся к цифровым услугам.\n"
    "• Баланс Stars пополняется моментально после подтверждения оплаты в Telegram.\n"
    "• Поскольку услуга предоставляется сразу, возврат средств возможен только по запросу в поддержку с анализом ситуации.\n"
    "• Используйте одного и того же Telegram-аккаунта при оплате и работе с кабинетом NutriBot.\n"
    "• Задавая оплату, вы подтверждаете, что ознакомлены с этими условиями и соглашением NutriBot.\n\n"
    "Нужна помощь? Напишите нам через команду /paysupport."
)

_SUPPORT_TEXT = (
    "Команда NutriBot на связи!\n\n"
    "— Общие вопросы: напишите куратору в <a href=\"https://t.me/CaloIQ_bot\">@CaloIQ_bot</a> или на почту support@nutribot.example.\n"
    "— По спорным ситуациям мы отвечаем в течение 24 часов в рабочие дни."
)

_PAY_SUPPORT_TEXT = (
    "Если возникла проблема с оплатой Stars:\n\n"
    "1. Сохраните чек Telegram (кнопка «Показать квитанцию»).\n"
    "2. Отправьте детали (ID платежа, сумму, дату) нашему куратору в <a href=\"https://t.me/CaloIQ_bot\">@CaloIQ_bot</a>\n"
    "   или на почту support@nutribot.example.\n"
    "3. Мы проверим списание и свяжемся с вами — обычно в течение рабочего дня."
)


@router.message(Command("terms"))
async def terms_command(message: Message) -> None:
    await message.answer(_TERMS_TEXT)


@router.message(Command("support"))
async def support_command(message: Message) -> None:
    await message.answer(_SUPPORT_TEXT)


@router.message(Command("paysupport"))
async def pay_support_command(message: Message) -> None:
    await message.answer(_PAY_SUPPORT_TEXT)