from aiogram.types import InlineKeyboardMarkup, WebAppInfo

from bot.handlers.profile_wizard import _build_authorization_markup


def test_build_authorization_markup_uses_webapp_bridge():
    markup = _build_authorization_markup("https://example.com/webapp/")
    assert isinstance(markup, InlineKeyboardMarkup)
    button = markup.inline_keyboard[0][0]
    assert button.text == "Открыть анкету"
    assert isinstance(button.web_app, WebAppInfo)
    assert button.web_app.url == "https://example.com/webapp/auth-bridge"


def test_build_authorization_markup_falls_back_to_url_for_non_https():
    markup = _build_authorization_markup("http://localhost:5173")
    button = markup.inline_keyboard[0][0]
    assert button.web_app is None
    assert button.url == "http://localhost:5173/auth-bridge"
