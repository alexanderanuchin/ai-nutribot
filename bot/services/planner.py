from typing import List, Dict
from .models import MenuItem, Profile
from .nutrition import Targets, tdee

def filter_items(items: List[MenuItem], p: Profile) -> List[MenuItem]:
    res = []
    for it in items:
        if p.allergies and (set(it.allergens) & set(p.allergies)): 
            continue
        if p.exclusions and (set(it.exclusions) & set(p.exclusions)):
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
