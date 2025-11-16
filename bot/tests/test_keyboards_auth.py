from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.auth import build_authorize_keyboard


def test_build_authorize_keyboard_appends_bridge_path():
    markup = build_authorize_keyboard("https://example.com/webapp/")
    assert isinstance(markup, ReplyKeyboardMarkup)
    button = markup.keyboard[0][0]
    assert button.text == "Авторизоваться"
    assert button.web_app and button.web_app.url == "https://example.com/webapp/auth-bridge"


def test_build_authorize_keyboard_handles_empty_url():
    markup = build_authorize_keyboard("")
    button = markup.keyboard[0][0]
    assert button.web_app is None
