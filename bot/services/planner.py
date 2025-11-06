import re
import unicodedata
from typing import Dict, Iterable, List
from .models import MenuItem, Profile
from .nutrition import Targets, tdee

MIN_TERM_LENGTH = 3
STOPWORDS = {"без", "и", "или", "the", "and", "with", "та", "на", "по", "от"}


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    lowered = without_marks.lower()
    sanitized = re.sub(r"[^a-zа-яё0-9\s]", " ", lowered)
    collapsed = re.sub(r"\s+", " ", sanitized).strip()
    return collapsed


def _tokenize_preferences(values: List[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values or []:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        for token in re.split(r"[\s,;/]+", normalized):
            token = token.strip()
            if len(token) < MIN_TERM_LENGTH or token in STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _normalize_collection(values: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = _normalize_text(value)
        if text:
            normalized.append(text)
    return normalized


def _contains_forbidden(texts: List[str], forbidden_tokens: set[str]) -> bool:
    if not forbidden_tokens:
        return False
    for text in texts:
        for token in forbidden_tokens:
            if token in text:
                return True
    return False


def filter_items(items: List[MenuItem], p: Profile) -> List[MenuItem]:
    allergy_tokens = _tokenize_preferences(p.allergies)
    exclusion_tokens = _tokenize_preferences(p.exclusions)
    res = []
    for it in items:
        allergen_texts = _normalize_collection(it.allergens)
        if _contains_forbidden(allergen_texts, allergy_tokens):
            continue
        exclusion_texts = _normalize_collection(it.exclusions)
        if _contains_forbidden(exclusion_texts, exclusion_tokens):
            continue
        if p.daily_budget and it.price and it.price > p.daily_budget:
            continue
        res.append(it)
    return res

def greedy_knapsack(items: List[MenuItem], targets: Targets) -> List[Dict]:
    picked: List[Dict] = []
    remain = targets.calories
    # сортируем по близости к одной порции, предполагая 3 приема пищи
    for it in sorted(items, key=lambda x: abs(x.nutrients["calories"] - remain/3)):
        if remain <= 0: break
        c = max(1.0, round(remain / max(1.0, it.nutrients["calories"])))
        qty = min(c, 3.0)
        picked.append({"item_id": it.id, "title": it.title, "qty": qty, "time_hint": "any"})
        remain -= int(it.nutrients["calories"] * qty)
        if len(picked) >= 6:  # ограничим длину
            break
    return picked

def build_menu(items: List[MenuItem], p: Profile) -> Dict:
    tg = tdee(p.sex, p.weight_kg, p.height_cm, p.birth_date, p.activity_level, p.goal)
    filtered = filter_items(items, p)
    if not filtered:
        return {"targets": tg.__dict__, "plan": []}
    plan = greedy_knapsack(filtered, tg)
    return {"targets": tg.__dict__, "plan": plan}
