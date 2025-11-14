from __future__ import annotations

START_TITLE = "<b>NutriBot Mini App</b>"
START_LEAD = (
    "Запускайте мини-приложение, чтобы управлять профилем, планами и кошельком Stars"
    " в одном месте."
)
START_AUTH_HINT = "Вы авторизованы — выбирайте раздел ниже."
START_AUTH_REQUIRED = (
    "Чтобы начать, войдите через мини-приложение — оно откроется по кнопке выше."
)
CANCELLED_TEXT = "Текущий шаг отменён. Меню снова открыто ниже."
THROTTLED_TEXT = "Слишком часто, попробуйте позже."
ERROR_TEXT = (
    "Что-то пошло не так. Мы уже работаем над проблемой."
    "\nПопробуйте повторить действие позже."
)


def build_start_message(*, authorized: bool) -> str:
    lines = [START_TITLE, START_LEAD]
    lines.append(START_AUTH_HINT if authorized else START_AUTH_REQUIRED)
    return "\n".join(lines)


__all__ = [
    "build_start_message",
    "CANCELLED_TEXT",
    "ERROR_TEXT",
    "START_LEAD",
    "START_TITLE",
    "START_AUTH_HINT",
    "START_AUTH_REQUIRED",
    "THROTTLED_TEXT",
]
