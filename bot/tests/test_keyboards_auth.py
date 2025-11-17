from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.auth import build_auth_bridge_url, build_authorize_keyboard


def test_build_auth_bridge_url_appends_path_and_trims_slash():
    assert (
        build_auth_bridge_url("https://example.com/webapp/")
        == "https://example.com/webapp/auth-bridge"
    )


def test_build_auth_bridge_url_handles_empty_value():
    assert build_auth_bridge_url("") is None


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
