from __future__ import annotations

from dataclasses import replace

import pytest

from apps.catalog.etl.usda import (
    ExternalMenuItem,
    NutrientProfile,
    USDAFoodImporter,
    USDAFoodLoader,
    USDAFoodTransformer,
)
from apps.catalog.models import MenuItem, Store


@pytest.fixture
def sample_entry() -> dict:
    return {
        "id": 4242,
        "description": "Greek yogurt with blueberries",
        "group": "Dairy and Egg Products",
        "manufacturer": "Nordic Cultures",
        "tags": ["breakfast", "superfood"],
        "portions": [
            {"amount": 1, "unit": "cup", "grams": 150},
        ],
        "nutrients": [
            {"description": "Energy", "units": "kcal", "value": 190},
            {"description": "Protein", "units": "g", "value": 18},
            {"description": "Total lipid (fat)", "units": "g", "value": 5},
            {"description": "Carbohydrate, by difference", "units": "g", "value": 22},
            {"description": "Fiber, total dietary", "units": "g", "value": 2.5},
            {"description": "Sodium, Na", "units": "mg", "value": 75},
        ],
    }


def test_transformer_enriches_usda_entry(sample_entry):
    transformer = USDAFoodTransformer(min_calories=100)
    items = list(transformer.transform([sample_entry]))
    assert len(items) == 1
    item = items[0]
    assert item.external_id == "usda-4242"
    assert item.nutrients.calories == pytest.approx(190)
    assert "dairy-and-egg-products" in item.tags
    assert "milk" in item.allergens
    assert item.price >= 150
    assert "Категория" in item.description


@pytest.mark.django_db
def test_loader_creates_and_updates_records():
    loader = USDAFoodLoader()
    profile = NutrientProfile(calories=400, protein=30, fat=12, carbs=35, fiber=6, sodium=350)
    item = ExternalMenuItem(
        external_id="usda-test-item",
        title="Test entrée",
        description="Savory bowl with grains and tofu.",
        price=420,
        tags=["test", "bowl"],
        allergens=["soy"],
        exclusions=["gluten-free"],
        nutrients=profile,
        store_name="Future Foods",
        store_city="Москва",
    )

    created, updated = loader.load([item])
    assert created == 1
    assert updated == 0
    saved = MenuItem.objects.get()
    assert saved.price == 420
    assert saved.nutrients.calories == pytest.approx(400)
    assert Store.objects.filter(name="Future Foods").exists()

    updated_item = replace(
        item,
        price=510,
        nutrients=NutrientProfile(calories=420, protein=32, fat=14, carbs=40, fiber=7, sodium=360),
    )
    created, updated = loader.load([updated_item])
    assert created == 0
    assert updated == 1
    saved.refresh_from_db()
    assert saved.price == 510
    assert saved.nutrients.calories == pytest.approx(420)


class _DummyExtractor:
    def __init__(self, payload: list[dict]):
        self.payload = payload

    def fetch(self) -> list[dict]:
        return self.payload


def test_importer_dry_run(sample_entry):
    extractor = _DummyExtractor([sample_entry])
    transformer = USDAFoodTransformer(min_calories=100)
    importer = USDAFoodImporter(extractor=extractor, transformer=transformer)

    result = importer.run(limit=10, dry_run=True)

    assert result["total"] == 1
    assert len(result["preview"]) == 1
    assert isinstance(result["preview"][0], ExternalMenuItem)