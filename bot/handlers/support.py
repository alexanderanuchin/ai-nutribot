from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def _format_terms_text(*, terms_url: str | None, privacy_url: str | None) -> str:
    lines = ["<b>Условия использования Stars</b>"]
    lines.append(
        "Покупки совершаются в Telegram Stars (XTR). После подтверждения оплата обрабатывается моментально."
    )
    lines.append(
        "Возврат возможен только через поддержку после проверки ситуации, поскольку услуга оказывается сразу."
    )
    if terms_url:
        lines.append(f"📄 Полная оферта: {terms_url}")
    if privacy_url:
        lines.append(f"🔐 Политика конфиденциальности: {privacy_url}")
    lines.append("Для вопросов по оплате используйте раздел поддержки.")
    return "\n\n".join(lines)


def _format_support_text(*, support_url: str | None) -> str:
    lines = ["Команда NutriBot на связи!"]
    if support_url:
        lines.append(f"Связаться в один клик: {support_url}")
    lines.append(
        "Если ссылка недоступна — напишите куратору @CaloIQ_bot или на почту support@nutribot.example."
    )
    lines.append("Мы отвечаем в течение рабочего дня.")
    return "\n\n".join(lines)


def _format_pay_support_text(*, support_url: str | None) -> str:
    lines = ["Если возникла проблема с оплатой Stars:"]
    lines.append("1. Сохраните чек в Telegram (кнопка «Показать квитанцию»).")
    if support_url:
        lines.append(f"2. Отправьте ID платежа и сумму через {support_url}.")
    else:
        lines.append("2. Отправьте ID платежа и сумму куратору @CaloIQ_bot или на почту support@nutribot.example.")
    lines.append("3. Мы проверим списание и вернёмся с ответом — обычно в течение рабочего дня.")
    return "\n\n".join(lines)


def _format_info_legal_text(*, terms_url: str | None, privacy_url: str | None, support_url: str | None) -> str:
    lines = ["<b>ℹ️ Info & Legal</b>"]
    lines.append("NutriBot работает в Telegram Stars — документы и поддержка ниже.")
    resources: list[str] = []
    if privacy_url:
        resources.append(f"🔐 <a href=\"{privacy_url}\">Privacy Policy</a>")
    if terms_url:
        resources.append(f"📄 <a href=\"{terms_url}\">Terms of Service</a>")
    if support_url:
        resources.append(f"🆘 <a href=\"{support_url}\">Support Centre</a>")
    if resources:
        lines.append("\n".join(resources))
    lines.append("Нужно больше деталей — нажмите «Задать вопрос».")
    return "\n\n".join(lines)


def build_info_legal_keyboard(
    *,
    support_url: str | None,
    webapp_url: str | None,
    browser_url: str | None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if browser_url:
        builder.button(text="🌐 Открыть в браузере", url=browser_url)
    if support_url:
        builder.button(text="Задать вопрос", url=support_url)
    elif webapp_url:
        cleaned = webapp_url.strip()
        if cleaned.lower().startswith("https://"):
            builder.button(text="Задать вопрос", web_app=WebAppInfo(url=cleaned))
        else:
            builder.button(text="Задать вопрос", url=cleaned)
    builder.button(text="↩️ В меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


async def send_info_legal(
    message: Message,
    *,
    terms_url: str | None,
    privacy_url: str | None,
    support_url: str | None,
    webapp_url: str | None,
    browser_url: str | None,
) -> None:
    await message.answer(
        _format_info_legal_text(
            terms_url=terms_url,
            privacy_url=privacy_url,
            support_url=support_url,
        ),
        reply_markup=build_info_legal_keyboard(
            support_url=support_url,
            webapp_url=webapp_url,
            browser_url=browser_url,
        ),
    )


@router.message(Command("terms"))
async def terms_command(
    message: Message,
    *,
    terms_url: str | None = None,
    privacy_url: str | None = None,
) -> None:
    await message.answer(_format_terms_text(terms_url=terms_url, privacy_url=privacy_url))


@router.message(Command("support"))
async def support_command(
    message: Message,
    *,
    support_url: str | None = None,
) -> None:
    await message.answer(_format_support_text(support_url=support_url))


@router.message(Command("paysupport"))
async def pay_support_command(
    message: Message,
    *,
    support_url: str | None = None,
) -> None:
    await message.answer(_format_pay_support_text(support_url=support_url))


__all__ = [
    "router",
    "terms_command",
    "support_command",
    "pay_support_command",
    "build_info_legal_keyboard",
    "send_info_legal",
]
