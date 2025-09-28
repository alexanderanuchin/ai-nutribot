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

## JWT authentication secrets

Simple JWT is configured to sign access and refresh tokens with the value of the `JWT_SECRET` environment variable. If the variable is missing, Django will fall back to `DJANGO_SECRET_KEY`, which means that rotating either secret will instantly invalidate every issued token.

- Always provide a stable `JWT_SECRET` in your runtime environment (for example via `infra/.env`).
- After rotating the signing key, clear the cached tokens in your browser (`nutribot_access` / `nutribot_refresh`) and sign in again so that the backend can issue new JWTs.
- If you run the project with Docker Compose, make sure the backend container receives the same `JWT_SECRET` value across restarts to avoid unexpected 401 responses for active sessions.