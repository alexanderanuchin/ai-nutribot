import json
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.catalog.models import Restaurant, Store, MenuItem, Nutrients

class Command(BaseCommand):
    help = "Load seed restaurants and products from seeds/*.json"

    def handle(self, *args, **kwargs):
        base = Path(__file__).resolve().parents[4] / "seeds"
        rest_file = base / "restaurants.json"
        prod_file = base / "products.json"

        if rest_file.exists():
            data = json.loads(rest_file.read_text("utf-8"))
            for r in data:
                Restaurant.objects.update_or_create(
                    id=r.get("id"),
                    defaults={"name": r["name"], "city": r.get("city", "Москва")},
                )
            self.stdout.write(self.style.SUCCESS(f"Restaurants loaded: {len(data)}"))

        if prod_file.exists():
            data = json.loads(prod_file.read_text("utf-8"))
            created = 0
            for p in data:
                n = p["nutrients"]
                nutrients = Nutrients.objects.create(
                    calories=n["calories"], protein=n["protein"], fat=n["fat"], carbs=n["carbs"],
                    fiber=n.get("fiber",0), sodium=n.get("sodium",0)
                )
                MenuItem.objects.create(
                    source=p["source"], source_id=p["source_id"], title=p["title"], price=p.get("price",0),
                    tags=p.get("tags",[]), allergens=p.get("allergens",[]), exclusions=p.get("exclusions",[]),
                    nutrients=nutrients
                )
                created += 1
            self.stdout.write(self.style.SUCCESS(f"Menu items loaded: {created}"))
