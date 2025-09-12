from dataclasses import dataclass
from typing import List, Optional, TypedDict

class Nutrients(TypedDict):
    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: float
    sodium: float

@dataclass
class MenuItem:
    id: int
    title: str
    price: int
    tags: list[str]
    allergens: list[str]
    exclusions: list[str]
    nutrients: Nutrients

@dataclass
class Profile:
    sex: str                 # 'm' | 'f'
    birth_date: Optional[str]
    height_cm: int
    weight_kg: float
    activity_level: str      # sedentary/light/moderate/high/athlete
    goal: str                # lose/maintain/gain/recomp
    allergies: List[str]
    exclusions: List[str]
    daily_budget: Optional[int]
