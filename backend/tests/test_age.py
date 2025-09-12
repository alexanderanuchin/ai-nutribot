from datetime import date

from apps.nutrition.services import age


def test_age_none_returns_default():
    assert age(None) == 30


def test_age_calculation():
    today = date.today()
    birth = today.replace(year=today.year - 20)
    assert age(birth) == 20