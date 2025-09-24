from __future__ import annotations

from typing import Dict

from .menu_filters import MenuFilterService
from .menu_selection import MenuSelectionService
from .services import tdee

default_filter_service = MenuFilterService()
default_selection_service = MenuSelectionService()


def build_menu_for_user(
        user,
        *,
        filter_service: MenuFilterService | None = None,
        selection_service: MenuSelectionService | None = None,
) -> Dict:
    """Build a daily menu for the given user profile."""
    filter_service = filter_service or default_filter_service
    selection_service = selection_service or default_selection_service

    profile = user.profile
    targets = tdee(
        profile.sex,
        profile.weight_kg,
        profile.height_cm,
        profile.birth_date,
        profile.activity_level,
        profile.goal,
    )

    items = filter_service.filter(
        city=getattr(user, "city", None),
        allergies=profile.allergies,
        exclusions=profile.exclusions,
        budget=profile.daily_budget,
    )

    restrictions = {
        "allergies": profile.allergies,
        "exclusions": profile.exclusions,
    }

    plan = selection_service.select_plan(
        items=items,
        targets=targets,
        restrictions=restrictions,
    )

    return {
        "targets": selection_service.serialize_targets(targets),
        "plan": plan,
    }
