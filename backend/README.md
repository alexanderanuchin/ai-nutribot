# NutriboT backend quickstart

## Seeding the catalogue

```
USE_SQLITE=1 python manage.py migrate
USE_SQLITE=1 python manage.py load_seeds
```

Seed files live in `backend/seeds` and contain sample restaurants, stores and menu items with macro nutrients, allergens and lifestyle tags.

## USDA catalogue importer

Synchronise with the USDA open food composition dataset:

```
USE_SQLITE=1 python manage.py sync_usda_catalog --limit 150 --min-calories 180
```

The command downloads the JSON snapshot hosted on GitHub, enriches the entries with heuristically inferred allergens, tags and smart price estimations, then persists the result into `MenuItem`/`Nutrients`/`Store` tables. Re-run the command to receive incremental updates.

To execute the import asynchronously you can dispatch the Celery task `catalog.sync_usda_catalog` with optional `limit` or `dry_run` arguments.