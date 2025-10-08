from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
)
from urllib.parse import urlparse
import ipaddress

router = Router()

def _is_public_host(host: str) -> bool:
    if not host:
        return False
    h = host.lower()
    # Явно запрещаем локальные хосты
    if h == "localhost" or h.endswith(".local"):
        return False
    # IP адрес?
    try:
        ip = ipaddress.ip_address(h)
        # Только глобальные IP разрешим как "публичные"
        return ip.is_global
    except ValueError:
        # Не IP — похоже на доменное имя. Считаем публичным.
        return True

def _is_https_public(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    return p.scheme == "https" and _is_public_host(p.hostname)

def menu_kb(url: str) -> InlineKeyboardMarkup:
    rows = []
    # Кнопки с URL добавляем ТОЛЬКО для публичного HTTPS
    if _is_https_public(url):
        rows.append([InlineKeyboardButton(text="🔗 Открыть кабинет (встроенно)", web_app=WebAppInfo(url=url))])
        rows.append([InlineKeyboardButton(text="🌐 Открыть в браузере", url=url)])
    rows.append([InlineKeyboardButton(text="⭐ Кошелёк", callback_data="wallet:open")])
    rows.append([InlineKeyboardButton(text="🧭 Заполнить профиль", callback_data="wizard:start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _compose_menu_text(base: str, url: str) -> str:
    if _is_https_public(url):
        return base
    # Фоллбек для локалки/HTTP: даём копируемую ссылку текстом
    return (
        base
        + "\n\n⚠️ Telegram запрещает кнопки для локальных/не-HTTPS ссылок."
          "\nСкопируйте и откройте в браузере:"
          f"\n{url}"
    )

@router.message(CommandStart())
async def cmd_start(message: Message, webapp_url: str):
    await message.answer(
        _compose_menu_text("Привет! Выбери действие:", webapp_url),
        reply_markup=menu_kb(webapp_url),
    )

@router.message(Command("menu"))
async def cmd_menu(message: Message, webapp_url: str):
    await message.answer(
        _compose_menu_text("Меню:", webapp_url),
        reply_markup=menu_kb(webapp_url),
    )

@router.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, webapp_url: str):
    await cb.message.edit_text(
        _compose_menu_text("Меню:", webapp_url),
        reply_markup=menu_kb(webapp_url),
    )
    await cb.answer()
