"""ETL pipeline for the public USDA food composition dataset.

The USDA food database is distributed with the book "Python for Data Analysis"
by Wes McKinney. We use the curated JSON dump hosted on GitHub to bootstrap a
rich product catalogue with macro nutrients, allergen hints and pricing
estimates. The module exposes a classic Extract/Transform/Load workflow that can
be reused by management commands and Celery tasks.
"""
from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from itertools import islice
from typing import Iterable, Iterator, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.db import transaction

from apps.catalog.models import MenuItem, Nutrients, Store

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/wesm/pydata-book/2nd-edition/"
    "datasets/usda_food/database.json"
)
CITY_POOL = [
    "Москва",
    "Санкт-Петербург",
    "Екатеринбург",
    "Новосибирск",
    "Казань",
    "Нижний Новгород",
    "Краснодар",
]
ALLERGEN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "milk": ("milk", "cheese", "cream", "yogurt", "butter", "casein"),
    "egg": ("egg", "albumen", "ovum"),
    "soy": ("soy", "soja", "tofu", "edamame"),
    "nuts": ("almond", "nut", "peanut", "cashew", "walnut", "hazelnut", "pecan"),
    "gluten": ("wheat", "barley", "rye", "spelt", "triticale", "gluten"),
    "fish": ("salmon", "trout", "tuna", "cod", "anchovy", "fish"),
    "shellfish": ("shrimp", "prawn", "mussel", "clam", "lobster", "crab", "scallop"),
    "sesame": ("sesame", "tahini"),
}
MEAT_KEYWORDS: tuple[str, ...] = (
    "beef",
    "pork",
    "bacon",
    "ham",
    "lamb",
    "chicken",
    "turkey",
    "duck",
    "goose",
)
FISH_KEYWORDS: tuple[str, ...] = (
    "salmon",
    "tuna",
    "cod",
    "trout",
    "herring",
    "anchovy",
    "mackerel",
    "sardine",
    "shrimp",
    "prawn",
)


@dataclass(frozen=True)
class NutrientProfile:
    """A normalized view of macro nutrient information for a menu item."""

    calories: float
    protein: float
    fat: float
    carbs: float
    fiber: float
    sodium: float

    def as_dict(self) -> dict[str, float]:
        return {
            "calories": float(self.calories),
            "protein": float(self.protein),
            "fat": float(self.fat),
            "carbs": float(self.carbs),
            "fiber": float(self.fiber),
            "sodium": float(self.sodium),
        }


@dataclass(frozen=True)
class ExternalMenuItem:
    """Domain object produced by the transformer and consumed by the loader."""

    external_id: str
    title: str
    description: str
    price: int
    tags: list[str]
    allergens: list[str]
    exclusions: list[str]
    nutrients: NutrientProfile
    store_name: str
    store_city: str

    @property
    def source(self) -> str:
        return "store"


class USDAFoodExtractor:
    """Download the USDA dataset from GitHub."""

    def __init__(
        self,
        *,
        source_url: str = DEFAULT_SOURCE_URL,
        timeout: int = 60,
        user_agent: str = "ai-nutribot-etl/1.0",
    ) -> None:
        self.source_url = source_url
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(self) -> list[dict]:
        request = Request(self.source_url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset("utf-8")
                payload = response.read().decode(charset)
        except HTTPError as exc:
            raise RuntimeError(
                f"Failed to fetch USDA dataset (status {exc.code})"
            ) from exc
        except URLError as exc:
            raise RuntimeError("Failed to reach USDA dataset host") from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Received malformed USDA dataset JSON") from exc


class USDAFoodTransformer:
    """Convert raw USDA entries into enriched menu items."""

    DEFAULT_GROUPS = {
        "Dairy and Egg Products",
        "Fast Foods",
        "Soups, Sauces, and Gravies",
        "Vegetables and Vegetable Products",
        "Fruits and Fruit Juices",
        "Breakfast Cereals",
        "Legumes and Legume Products",
        "Nut and Seed Products",
        "Cereal Grains and Pasta",
    }

    def __init__(
        self,
        *,
        allowed_groups: Sequence[str] | None = None,
        min_calories: float = 150.0,
        max_items: int | None = None,
    ) -> None:
        self.allowed_groups = set(allowed_groups) if allowed_groups else set(self.DEFAULT_GROUPS)
        self.min_calories = float(min_calories)
        self.max_items = max_items

    def transform(self, rows: Sequence[Mapping[str, object]]) -> Iterator[ExternalMenuItem]:
        processed = 0
        for entry in rows:
            if self.max_items is not None and processed >= self.max_items:
                break
            group = str(entry.get("group") or "").strip()
            if group and group not in self.allowed_groups:
                continue

            raw_description = str(entry.get("description") or "").strip()
            if not raw_description:
                continue

            nutrients = self._extract_nutrients(entry.get("nutrients"))
            if not nutrients or nutrients.calories < self.min_calories:
                continue

            manufacturer = str(entry.get("manufacturer") or "").strip()
            tags = self._collect_tags(raw_description, group, manufacturer, entry.get("tags"))
            allergens = self._detect_allergens(raw_description, group, tags)
            exclusions = self._derive_exclusions(tags, allergens)
            description = self._build_description(raw_description, group, entry.get("portions"))
            price = self._estimate_price(nutrients)
            store_name = self._resolve_store_name(group, manufacturer)
            store_city = self._resolve_store_city(store_name)
            external_id = f"usda-{entry.get('id')}"

            menu_item = ExternalMenuItem(
                external_id=external_id,
                title=self._format_title(raw_description),
                description=description,
                price=price,
                tags=tags,
                allergens=allergens,
                exclusions=exclusions,
                nutrients=nutrients,
                store_name=store_name,
                store_city=store_city,
            )
            processed += 1
            yield menu_item

    def _extract_nutrients(self, payload: object) -> NutrientProfile | None:
        if not isinstance(payload, Sequence):
            return None
        calories = protein = fat = carbs = fiber = sodium = None
        for nutrient in payload:
            if not isinstance(nutrient, Mapping):
                continue
            description = str(nutrient.get("description") or "")
            units = str(nutrient.get("units") or "")
            value = nutrient.get("value")
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if description == "Energy" and units == "kcal":
                calories = numeric
            elif description == "Protein":
                protein = numeric
            elif description == "Total lipid (fat)":
                fat = numeric
            elif description == "Carbohydrate, by difference":
                carbs = numeric
            elif description == "Fiber, total dietary":
                fiber = numeric
            elif description == "Sodium, Na":
                sodium = numeric
        if calories is None or protein is None or fat is None or carbs is None:
            return None
        return NutrientProfile(
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            fiber=fiber or 0.0,
            sodium=sodium or 0.0,
        )

    def _collect_tags(
        self,
        description: str,
        group: str,
        manufacturer: str,
        extra: object,
    ) -> list[str]:
        tags = {
            self._slugify(group),
            "usda",
        }
        if manufacturer:
            tags.add(self._slugify(manufacturer))
        if isinstance(extra, Sequence):
            for entry in extra:
                if isinstance(entry, str) and entry:
                    tags.add(self._slugify(entry))
        text = description.lower()
        if any(keyword in text for keyword in ("vegan", "plant")):
            tags.add("plant-based")
        if any(keyword in text for keyword in ("spice", "chili", "pepper")):
            tags.add("spicy")
        if "salad" in text or "bowl" in text:
            tags.add("bowl")
        if "soup" in text:
            tags.add("soup")
        return sorted(tag for tag in tags if tag)

    def _detect_allergens(self, description: str, group: str, tags: Sequence[str]) -> list[str]:
        haystack = f"{description} {' '.join(tags)} {group}".lower()
        allergens = set()
        for allergen, keywords in ALLERGEN_KEYWORDS.items():
            if any(keyword in haystack for keyword in keywords):
                allergens.add(allergen)
        if "dairy" in group.lower():
            allergens.add("milk")
        if "egg" in group.lower():
            allergens.add("egg")
        if "nut" in group.lower():
            allergens.add("nuts")
        if "seafood" in group.lower():
            allergens.add("fish")
        return sorted(allergens)

    def _derive_exclusions(self, tags: Sequence[str], allergens: Sequence[str]) -> list[str]:
        exclusions = set()
        text = " ".join(tags)
        if any(keyword in text for keyword in MEAT_KEYWORDS):
            exclusions.update({"vegan", "vegetarian"})
        if any(keyword in text for keyword in FISH_KEYWORDS):
            exclusions.add("vegan")
        if "milk" in allergens:
            exclusions.add("lactose-free")
            exclusions.add("vegan")
        if "gluten" in allergens:
            exclusions.add("gluten-free")
        if "nuts" in allergens:
            exclusions.add("nut-free")
        if "soy" in allergens:
            exclusions.add("soy-free")
        return sorted(exclusions)

    def _build_description(
        self,
        description: str,
        group: str,
        portions: object,
    ) -> str:
        portion_text = ""
        if isinstance(portions, Sequence) and portions:
            first = portions[0]
            if isinstance(first, Mapping):
                amount = first.get("amount")
                unit = first.get("unit")
                grams = first.get("grams")
                if amount and unit:
                    portion_text = f"Порция: {amount} {unit}".strip()
                if grams:
                    portion_text = f"{portion_text} ({grams} г)".strip()
        base = description
        if portion_text:
            base = f"{base}. {portion_text}."
        else:
            base = f"{base}."
        if group:
            base = f"{base} Категория: {group}."
        return base

    def _estimate_price(self, nutrients: NutrientProfile) -> int:
        base = nutrients.calories * 0.42 + nutrients.protein * 7.5 + nutrients.fiber * 2
        premium = 0
        if nutrients.protein >= 25:
            premium += 40
        if nutrients.fiber >= 8:
            premium += 25
        if nutrients.fat <= 12:
            premium += 20
        price = int(math.ceil((base + premium) / 10.0) * 10)
        return min(max(price, 150), 1500)

    def _resolve_store_name(self, group: str, manufacturer: str) -> str:
        if manufacturer:
            normalized = re.sub(r"\s+", " ", manufacturer).strip()
            return normalized[:120]
        if group:
            return f"{group} Collective"
        return "USDA Marketplace"

    def _resolve_store_city(self, name: str) -> str:
        digest = sum(ord(char) for char in name)
        return CITY_POOL[digest % len(CITY_POOL)]

    def _format_title(self, description: str) -> str:
        title = description.strip()
        if not title:
            return "USDA продукт"
        return title[:200]

    def _slugify(self, value: str) -> str:
        value = re.sub(r"[^0-9A-Za-zА-Яа-яёЁ]+", "-", value.strip().lower())
        return value.strip("-")


class USDAFoodLoader:
    """Persist transformed items into the catalogue tables."""

    def load(self, items: Iterable[ExternalMenuItem]) -> tuple[int, int]:
        created = 0
        updated = 0
        for item in items:
            with transaction.atomic():
                store, _ = Store.objects.get_or_create(
                    name=item.store_name,
                    defaults={"city": item.store_city},
                )
                try:
                    menu_obj = MenuItem.objects.select_for_update().get(
                        external_id=item.external_id
                    )
                except MenuItem.DoesNotExist:
                    nutrients = Nutrients.objects.create(**item.nutrients.as_dict())
                    MenuItem.objects.create(
                        external_id=item.external_id,
                        source=item.source,
                        source_id=store.id,
                        title=item.title,
                        description=item.description,
                        price=item.price,
                        is_available=True,
                        tags=list(item.tags),
                        allergens=list(item.allergens),
                        exclusions=list(item.exclusions),
                        nutrients=nutrients,
                    )
                    created += 1
                    continue

                menu_obj.source = item.source
                menu_obj.source_id = store.id
                menu_obj.title = item.title
                menu_obj.description = item.description
                menu_obj.price = item.price
                menu_obj.is_available = True
                menu_obj.tags = list(item.tags)
                menu_obj.allergens = list(item.allergens)
                menu_obj.exclusions = list(item.exclusions)
                menu_obj.save()
                if menu_obj.nutrients_id:
                    Nutrients.objects.filter(pk=menu_obj.nutrients_id).update(
                        **item.nutrients.as_dict()
                    )
                else:
                    menu_obj.nutrients = Nutrients.objects.create(**item.nutrients.as_dict())
                    menu_obj.save(update_fields=["nutrients"])
                updated += 1
        return created, updated


class USDAFoodImporter:
    """High level facade to run the ETL process end-to-end."""

    def __init__(
        self,
        extractor: USDAFoodExtractor | None = None,
        transformer: USDAFoodTransformer | None = None,
        loader: USDAFoodLoader | None = None,
    ) -> None:
        self.extractor = extractor or USDAFoodExtractor()
        self.transformer = transformer or USDAFoodTransformer()
        self.loader = loader or USDAFoodLoader()

    def run(
        self,
        *,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, object]:
        raw_rows = self.extractor.fetch()
        transformer = self.transformer
        if limit is not None:
            transformer = USDAFoodTransformer(
                allowed_groups=list(transformer.allowed_groups),
                min_calories=transformer.min_calories,
                max_items=limit,
            )
        items_iter = transformer.transform(raw_rows)
        if limit is not None:
            items_iter = islice(items_iter, limit)
        items = list(items_iter)
        if dry_run:
            logger.info("Dry run completed for %s items", len(items))
            preview = items[: min(len(items), 5)]
            return {
                "total": len(items),
                "preview": preview,
            }
        created, updated = self.loader.load(items)
        summary = {
            "created": created,
            "updated": updated,
            "total": created + updated,
        }
        logger.info(
            "USDA import finished: %s created, %s updated", created, updated
        )
        return summary


__all__ = [
    "DEFAULT_SOURCE_URL",
    "ExternalMenuItem",
    "NutrientProfile",
    "USDAFoodExtractor",
    "USDAFoodImporter",
    "USDAFoodLoader",
    "USDAFoodTransformer",
]