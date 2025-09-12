from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Targets:
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int


ACTIVITY = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "athlete": 1.9,
}

GOAL_ADJUST = {"lose": -0.2, "maintain": 0.0, "gain": 0.15, "recomp": -0.05}


def age(birth_date: Optional[date]) -> int:
    if not birth_date:
        return 30
    today = date.today()
    return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def tdee(
        sex: str,
        weight_kg: float,
        height_cm: int,
        birth_date: Optional[date],
        activity_level: str,
        goal: str,
) -> Targets:
    a = age(birth_date)
    if sex == "m":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * a + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * a - 161
    tdee_val = bmr * ACTIVITY.get(activity_level, 1.55)
    tdee_val *= 1.0 + GOAL_ADJUST.get(goal, 0.0)

    protein_g = int(round(1.8 * weight_kg))
    fat_kcal = int(0.25 * tdee_val)
    fat_g = int(round(fat_kcal / 9))
    protein_kcal = protein_g * 4
    carbs_kcal = max(0, int(tdee_val) - fat_kcal - protein_kcal)
    carbs_g = int(round(carbs_kcal / 4))

    return Targets(calories=int(tdee_val), protein_g=protein_g, fat_g=fat_g, carbs_g=carbs_g)
