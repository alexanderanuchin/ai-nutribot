from __future__ import annotations

START_TITLE = "<b>NutriBot · свежий опыт питания</b>"
START_LEAD = (
    "Персональные планы, контроль прогресса и кошелёк Stars — всё в одном мини-приложении."
)
START_CTA = "Нажмите «Открыть приложение», чтобы стартовать за минуту."
START_AUTH_HINT = "Вы уже в системе — выбирайте следующий шаг ниже."
START_AUTH_REQUIRED = "Чтобы продолжить, войдите через кнопку «Открыть приложение»."
CANCELLED_TEXT = "Текущий шаг отменён. Меню снова открыто ниже."
THROTTLED_TEXT = "Слишком часто, попробуйте позже."
ERROR_TEXT = (
    "Что-то пошло не так. Мы уже работаем над проблемой."
    "\nПопробуйте повторить действие позже."
)


def build_start_message(*, authorized: bool) -> str:
    lines = [START_TITLE, START_LEAD, START_CTA]
    lines.append(START_AUTH_HINT if authorized else START_AUTH_REQUIRED)
    return "\n".join(lines)


__all__ = [
    "build_start_message",
    "CANCELLED_TEXT",
    "ERROR_TEXT",
    "START_CTA",
    "START_LEAD",
    "START_TITLE",
    "START_AUTH_HINT",
    "START_AUTH_REQUIRED",
    "THROTTLED_TEXT",
]
