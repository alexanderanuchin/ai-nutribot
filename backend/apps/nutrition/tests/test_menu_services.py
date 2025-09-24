import sys
import types

if 'openai' not in sys.modules:
    openai_stub = types.ModuleType('openai')
    openai_stub.APIConnectionError = Exception
    openai_stub.APITimeoutError = Exception
    openai_stub.BadRequestError = Exception
    openai_stub.OpenAIError = Exception
    openai_stub.RateLimitError = Exception

    class _DummyOpenAI:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=lambda **kwargs: None)
            )

    openai_stub.OpenAI = _DummyOpenAI
    sys.modules['openai'] = openai_stub

import pytest

from apps.catalog.models import MenuItem, Nutrients, Restaurant, Store
from apps.nutrition.menu_filters import MenuFilterService
from apps.nutrition.menu_selection import MenuSelectionService
from apps.nutrition.services import Targets


@pytest.mark.django_db
def test_menu_filter_service_applies_constraints():
    moscow_restaurant = Restaurant.objects.create(name="Cafe", city="Москва", is_active=True)
    spb_restaurant = Restaurant.objects.create(name="Bistro", city="Санкт-Петербург", is_active=True)
    moscow_store = Store.objects.create(name="Shop", city="Москва", is_active=True)

    def make_item(*, source: str, source_id: int, title: str, price: int, allergens=None, exclusions=None):
        nutrients = Nutrients.objects.create(calories=500, protein=30, fat=20, carbs=40)
        return MenuItem.objects.create(
            source=source,
            source_id=source_id,
            title=title,
            price=price,
            allergens=allergens or [],
            exclusions=exclusions or [],
            nutrients=nutrients,
        )

    keeper = make_item(source="restaurant", source_id=moscow_restaurant.id, title="Салат", price=350)
    make_item(source="restaurant", source_id=spb_restaurant.id, title="Суп", price=250)
    make_item(
        source="restaurant",
        source_id=moscow_restaurant.id,
        title="Десерт",
        price=200,
        allergens=["nuts"],
    )
    make_item(
        source="store",
        source_id=moscow_store.id,
        title="Буррито",
        price=450,
        exclusions=["pork"],
    )
    make_item(source="store", source_id=moscow_store.id, title="Стейк", price=900)

    service = MenuFilterService()
    items = service.filter(
        city="Москва",
        allergies=["nuts"],
        exclusions=["pork"],
        budget=500,
    )

    assert len(items) == 1
    assert items[0] == keeper


@pytest.mark.django_db
def test_menu_selection_service_uses_fallback(monkeypatch):
    restaurant = Restaurant.objects.create(name="Test", city="Москва", is_active=True)
    nutrients = Nutrients.objects.create(calories=420, protein=32, fat=12, carbs=55)
    item = MenuItem.objects.create(
        source="restaurant",
        source_id=restaurant.id,
        title="Боул",
        price=380,
        nutrients=nutrients,
    )

    class DummyProvider:
        def __init__(self):
            self.calls = []

        def compose_menu(self, context):
            self.calls.append(context)
            return []

    captured: dict[str, object] = {}

    def fallback(items, targets):
        captured["items"] = items
        captured["targets"] = targets
        return [
            {
                "item_id": items[0].id,
                "qty": 1.0,
                "time_hint": "any",
                "title": items[0].title,
            }
        ]

    provider = DummyProvider()
    service = MenuSelectionService(
        provider_factory=lambda: provider,
        fallback_strategy=fallback,
        context_items_limit=5,
    )

    targets = Targets(calories=1800, protein_g=120, fat_g=60, carbs_g=200)
    plan = service.select_plan(
        items=[item],
        targets=targets,
        restrictions={"allergies": ["milk"]},
    )

    assert plan == [
        {"item_id": item.id, "qty": 1.0, "time_hint": "any", "title": "Боул"}
    ]
    assert captured["items"][0] == item
    assert captured["targets"] == targets

    assert len(provider.calls) == 1
    context = provider.calls[0]
    assert context["items"][0]["id"] == item.id
    assert context["targets"]["protein"] == targets.protein_g
    assert context["restrictions"]["allergies"] == ["milk"]
    assert context["restrictions"]["exclusions"] == []