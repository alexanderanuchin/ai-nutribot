from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from apps.common.permissions import HasBotKey
from apps.users.models import Profile
from .planner import build_menu_for_user
from .models import MenuPlan, PlanMeal
from apps.catalog.models import MenuItem

User = get_user_model()

@api_view(["POST"])
@permission_classes([HasBotKey])
def upsert_profile(request):
    """
    Body: {
      "telegram_id": 123,
      "profile": {... как на фронте/боте ...},
      "city": "Москва" (опц.)
    }
    """
    tg_id = request.data.get("telegram_id")
    prof = request.data.get("profile") or {}
    city = request.data.get("city") or ""

    if not tg_id or not isinstance(prof, dict):
        return Response({"detail":"telegram_id or profile missing"}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(telegram_id=tg_id, defaults={"username": f"tg_{tg_id}"})
    if city:
        user.city = city
        user.save(update_fields=["city"])

    p, _ = Profile.objects.get_or_create(user=user, defaults=dict(
        sex=prof.get("sex","m"),
        height_cm=prof.get("height_cm",175),
        weight_kg=prof.get("weight_kg",70),
        activity_level=prof.get("activity_level","moderate"),
        goal=prof.get("goal","recomp"),
    ))
    # Обновим поля
    for f in ["sex","birth_date","height_cm","weight_kg","body_fat_pct","activity_level","goal","allergies","exclusions","daily_budget"]:
        if f in prof:
            setattr(p, f, prof[f])
    p.save()
    return Response({"ok": True, "user_id": user.id})

@api_view(["POST"])
@permission_classes([HasBotKey])
def generate_and_save(request):
    """
    Body: { "telegram_id": 123 }
    Возвращает targets/plan и сохраняет MenuPlan/PlanMeal на сегодня.
    """
    tg_id = request.data.get("telegram_id")
    if not tg_id:
        return Response({"detail":"telegram_id missing"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(telegram_id=tg_id)
    except User.DoesNotExist:
        return Response({"detail":"user not found"}, status=status.HTTP_404_NOT_FOUND)

    data = build_menu_for_user(user)

    # Сохраним план
    today = date.today()
    plan = MenuPlan.objects.create(
        user=user,
        date=today,
        target_calories=data["targets"]["calories"],
        target_protein=data["targets"]["protein_g"],
        target_fat=data["targets"]["fat_g"],
        target_carbs=data["targets"]["carbs_g"],
        provider="hybrid"
    )
    for m in data["plan"]:
        try:
            item = MenuItem.objects.get(id=m["item_id"])
        except MenuItem.DoesNotExist:
            continue
        PlanMeal.objects.create(plan=plan, item=item, qty=float(m.get("qty",1)), time_hint=m.get("time_hint","any"))

    return Response(data)
