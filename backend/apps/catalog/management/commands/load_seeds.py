import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import MenuItem, Nutrients, Restaurant, Store


class Command(BaseCommand):
    help = "Load seed restaurants and products from seeds/*.json"

    def handle(self, *args, **kwargs):
        base = Path(__file__).resolve().parents[4] / "seeds"
        if not base.exists():
            raise CommandError("The seeds directory is missing. Expected to find backend/seeds")
        rest_file = base / "restaurants.json"
        store_file = base / "stores.json"
        prod_file = base / "products.json"

        if rest_file.exists():
            restaurants = json.loads(rest_file.read_text("utf-8"))
            for restaurant in restaurants:
                Restaurant.objects.update_or_create(
                    id=restaurant.get("id"),
                    defaults={
                        "name": restaurant["name"],
                        "city": restaurant.get("city", "Москва"),
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Restaurants loaded: {len(restaurants)}")
                )
            else:
                self.stdout.write("No restaurants.json seed file found")

        if store_file.exists():
            stores = json.loads(store_file.read_text("utf-8"))
            for store in stores:
                Store.objects.update_or_create(
                    id=store.get("id"),
                    defaults={
                        "name": store["name"],
                        "city": store.get("city", "Москва"),
                    },
                )
                self.stdout.write(self.style.SUCCESS(f"Stores loaded: {len(stores)}"))
            else:
                self.stdout.write("No stores.json seed file found")

            if prod_file.exists():
                products = json.loads(prod_file.read_text("utf-8"))
                created, updated = self._load_products(products)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Menu items processed: {len(products)} (created {created}, updated {updated})"
                    )
                )
            else:
                self.stdout.write("No products.json seed file found")

    def _load_products(self, items: list[dict]) -> tuple[int, int]:
        created = 0
        updated = 0

        for payload in items:
            nutrients_payload = payload.get("nutrients") or {}
            nutrients_defaults = {
                "calories": nutrients_payload.get("calories", 0),
                "protein": nutrients_payload.get("protein", 0),
                "fat": nutrients_payload.get("fat", 0),
                "carbs": nutrients_payload.get("carbs", 0),
                "fiber": nutrients_payload.get("fiber", 0),
                "sodium": nutrients_payload.get("sodium", 0),
            }

            menu_defaults = {
                "source": payload["source"],
                "source_id": payload["source_id"],
                "title": payload["title"],
                "description": payload.get("description", ""),
                "price": payload.get("price", 0),
                "is_available": payload.get("is_available", True),
                "tags": payload.get("tags", []),
                "allergens": payload.get("allergens", []),
                "exclusions": payload.get("exclusions", []),
            }

            identifier = payload.get("external_id")

            with transaction.atomic():
                if identifier:
                    item, was_created = MenuItem.objects.get_or_create(
                        external_id=identifier,
                        defaults=menu_defaults,
                    )
                else:
                    item, was_created = MenuItem.objects.get_or_create(
                        source=payload["source"],
                        source_id=payload["source_id"],
                        title=payload["title"],
                        defaults=menu_defaults,
                    )

                if was_created:
                    nutrients = Nutrients.objects.create(**nutrients_defaults)
                    item.nutrients = nutrients
                    item.save(update_fields=["nutrients"])
                    created += 1
                else:
                    for field, value in menu_defaults.items():
                        setattr(item, field, value)
                    item.save()
                    if item.nutrients_id:
                        Nutrients.objects.filter(pk=item.nutrients_id).update(
                            **nutrients_defaults
                        )
                    else:
                        item.nutrients = Nutrients.objects.create(**nutrients_defaults)
                        item.save(update_fields=["nutrients"])
                    updated += 1

        return created, updated
