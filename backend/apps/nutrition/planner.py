from typing import List, Dict
from apps.catalog.models import MenuItem
from .services import tdee, Targets
from .llm_provider import get_provider

def filter_items(city: str | None, allergies: list, exclusions: list, budget: int | None) -> List[MenuItem]:
    qs = MenuItem.objects.filter(is_available=True)
    if allergies:
        qs = qs.exclude(allergens__overlap=allergies)
    if exclusions:
        qs = qs.exclude(exclusions__overlap=exclusions)
    if budget:
        qs = qs.filter(price__lte=budget)
    return list(qs[:300])

def greedy_knapsack(items: List[MenuItem], targets: Targets) -> List[Dict]:
    picked = []
    remain = targets.calories
    for it in sorted(items, key=lambda x: abs(x.nutrients.calories - remain/3)):
        if remain <= 0:
            break
        qty = max(1.0, round(remain / max(1.0, it.nutrients.calories)))
        picked.append({"item_id": it.id, "title": it.title, "qty": min(qty, 3.0), "time_hint": "any"})
        remain -= int(it.nutrients.calories * min(qty, 3.0))
    return picked

def build_menu_for_user(user) -> Dict:
    prof = user.profile
    targets = tdee(prof.sex, prof.weight_kg, prof.height_cm, prof.birth_date, prof.activity_level, prof.goal)
    items = filter_items(getattr(user, "city", None), prof.allergies, prof.exclusions, prof.daily_budget)

    context = {
        "targets": targets.__dict__,
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "kcal": i.nutrients.calories,
                "protein": i.nutrients.protein,
                "fat": i.nutrients.fat,
                "carbs": i.nutrients.carbs,
                "tags": i.tags,
                "price": i.price,
            } for i in items[:120]
        ],
        "restrictions": {"allergies": prof.allergies, "exclusions": prof.exclusions},
    }

    try:
        plan = get_provider().compose_menu(context)
    except Exception:
        plan = []

    if not plan:
        plan = greedy_knapsack(items, targets)

    return {"targets": targets.__dict__, "plan": plan}
