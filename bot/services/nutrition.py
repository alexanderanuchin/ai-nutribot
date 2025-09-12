from dataclasses import dataclass
from datetime import date, datetime

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

def _age(birth_date: str | None) -> int:
    if not birth_date: return 30
    try:
        bd = datetime.strptime(birth_date,"%Y-%m-%d").date()
    except Exception:
        return 30
    today = date.today()
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

def tdee(sex: str, weight_kg: float, height_cm: int, birth_date: str | None, activity_level: str, goal: str) -> Targets:
    a = _age(birth_date)
    if sex == "m":
        bmr = 10*weight_kg + 6.25*height_cm - 5*a + 5
    else:
        bmr = 10*weight_kg + 6.25*height_cm - 5*a - 161
    t = bmr * ACTIVITY.get(activity_level, 1.55)
    t *= 1.0 + GOAL_ADJUST.get(goal, 0.0)
    protein_g = int(round(1.8 * weight_kg))
    fat_kcal = int(0.25 * t)
    fat_g = int(round(fat_kcal / 9))
    protein_kcal = protein_g * 4
    carbs_kcal = max(0, int(t) - fat_kcal - protein_kcal)
    carbs_g = int(round(carbs_kcal / 4))
    return Targets(calories=int(t), protein_g=protein_g, fat_g=fat_g, carbs_g=carbs_g)
