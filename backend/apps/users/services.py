from __future__ import annotations

import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Dict, List, Optional

from .models import Profile

ACTIVITY_FACTORS: Dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "active": 1.725,
    "athlete": 1.9,
}

GOAL_ADJUSTMENTS: Dict[str, int] = {
    "lose": -450,
    "maintain": 0,
    "gain": 350,
    "recomp": -150,
}

PROTEIN_RATIOS: Dict[str, Decimal] = {
    "gain": Decimal("0.28"),
    "lose": Decimal("0.32"),
    "recomp": Decimal("0.30"),
    "maintain": Decimal("0.20"),
}
DEFAULT_PROTEIN_RATIO = Decimal("0.20")

FAT_RATIOS: Dict[str, Decimal] = {
    "lose": Decimal("0.27"),
}
DEFAULT_FAT_RATIO = Decimal("0.28")

MIN_CALORIES = 1200


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def _round_decimal_to_int(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _format_ratio(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _age_from_birth_date(birth_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    today = date.today()
    years = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return years if years > 0 else None


def _format_age(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    mod10 = age % 10
    mod100 = age % 100
    if mod10 == 1 and mod100 != 11:
        return f"{age} год"
    if 2 <= mod10 <= 4 and (mod100 < 10 or mod100 >= 20):
        return f"{age} года"
    return f"{age} лет"


def _bmi_value(height_cm: Optional[int], weight_kg: Optional[Decimal]) -> Optional[float]:
    if not height_cm or height_cm <= 0 or weight_kg is None:
        return None
    try:
        height_m = Decimal(height_cm) / Decimal("100")
        if height_m <= 0:
            return None
        bmi = Decimal(weight_kg) / (height_m * height_m)
    except (InvalidOperation, ZeroDivisionError):
        return None
    bmi = bmi.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(bmi)


def _bmi_status(bmi: Optional[float]) -> Optional[str]:
    if bmi is None:
        return None
    bmi_value = Decimal(str(bmi))
    if bmi_value < Decimal("18.5"):
        return "Недостаточная масса"
    if bmi_value < Decimal("25"):
        return "Норма"
    if bmi_value < Decimal("30"):
        return "Избыточная масса"
    return "Требуется внимание"


def _macro_breakdown(calories: Optional[int], goal: str) -> List[Dict[str, Any]]:
    if not calories:
        return []
    protein_ratio = PROTEIN_RATIOS.get(goal, DEFAULT_PROTEIN_RATIO)
    fat_ratio = FAT_RATIOS.get(goal, DEFAULT_FAT_RATIO)
    carb_ratio = Decimal("1") - protein_ratio - fat_ratio
    if carb_ratio < Decimal("0"):
        carb_ratio = Decimal("0")

    calories_decimal = Decimal(calories)
    protein_g = _round_decimal_to_int((calories_decimal * protein_ratio) / Decimal("4"))
    fat_g = _round_decimal_to_int((calories_decimal * fat_ratio) / Decimal("9"))
    carbs_g = _round_decimal_to_int((calories_decimal * carb_ratio) / Decimal("4"))

    return [
        {"label": "Белки", "grams": protein_g, "ratio": _format_ratio(protein_ratio)},
        {"label": "Жиры", "grams": fat_g, "ratio": _format_ratio(fat_ratio)},
        {"label": "Углеводы", "grams": carbs_g, "ratio": _format_ratio(carb_ratio)},
    ]


def build_profile_metrics(profile: Profile) -> Dict[str, Any]:
    age_years = _age_from_birth_date(profile.birth_date)
    bmi = _bmi_value(profile.height_cm, profile.weight_kg)

    bmr: Optional[int] = None
    if profile.height_cm and profile.weight_kg:
        weight = float(profile.weight_kg)
        height = float(profile.height_cm)
        age_for_calc = age_years if age_years is not None else 30
        if profile.sex == Profile.Sex.FEMALE:
            base = 447.6 + 9.2 * weight + 3.1 * height - 4.3 * age_for_calc
        else:
            base = 88.36 + 13.4 * weight + 4.8 * height - 5.7 * age_for_calc
        bmr = _round_half_up(base)

    tdee: Optional[int] = None
    if bmr is not None:
        multiplier = ACTIVITY_FACTORS.get(profile.activity_level, 1.2)
        tdee = _round_half_up(bmr * multiplier)

    recommended_calories: Optional[int] = None
    if tdee is not None:
        adjustment = GOAL_ADJUSTMENTS.get(profile.goal, 0)
        recommended_calories = max(MIN_CALORIES, _round_half_up(tdee + adjustment))

    macros = _macro_breakdown(recommended_calories, profile.goal)

    return {
        "age": age_years,
        "age_display": _format_age(age_years),
        "bmi": bmi,
        "bmi_status": _bmi_status(bmi),
        "bmr": bmr,
        "tdee": tdee,
        "recommended_calories": recommended_calories,
        "macros": macros,
    }


__all__ = ["build_profile_metrics"]