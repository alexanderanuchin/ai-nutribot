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

## Nutrition plan worker

Menu generation tasks are executed by Celery. Ensure Redis is running (see `REDIS_URL`) and start a worker with:

```
USE_SQLITE=1 celery -A nutribot worker -l info -Q nutrition,celery
```

## Static typing

Run the focused mypy suite against the Django infrastructure and ETL/service helpers:

```
make typecheck
```

The target pre-configures `PYTHONPATH` and debug-friendly secrets so the checks can run without extra environment setup.

The nutrition endpoints rely on the following environment variables:

- `REDIS_URL` — broker/result backend for Celery (defaults to `redis://redis:6379/0`).
- `JWT_SECRET` — shared secret for issuing access/refresh tokens.
- `OPENAI_API_KEY` (optional) — enables the LLM-based planner; fallback heuristics are used otherwise.

### Quick manual check

1. Run `python manage.py migrate` and `python manage.py load_seeds`.
2. Start the Django dev server (`python manage.py runserver 0.0.0.0:8000`).
3. Launch the Celery worker as shown above.
4. Authorise via the WebApp or `/profile` flow, then in Telegram send `/plan` → выберите период → дождитесь генерации.
5. Кнопками «Принять»/«Отклонить» проверьте обновление статуса, затем `/history` для просмотра последних планов.

## JWT authentication secrets

Simple JWT is configured to sign access and refresh tokens with the value of the `JWT_SECRET` environment variable. If the variable is missing, Django will fall back to `DJANGO_SECRET_KEY`, which means that rotating either secret will instantly invalidate every issued token.

- Always provide a stable `JWT_SECRET` in your runtime environment (for example via `infra/.env`).
- After rotating the signing key, clear the cached tokens in your browser (`nutribot_access` / `nutribot_refresh`) and sign in again so that the backend can issue new JWTs.
- If you run the project with Docker Compose, make sure the backend container receives the same `JWT_SECRET` value across restarts to avoid unexpected 401 responses for active sessions.

## Feed admin console

### Как попасть в /admin

1. Выполните миграции:

   ```bash
   USE_SQLITE=1 python manage.py migrate
   ```

2. Создайте суперпользователя (или временный staff-аккаунт):

   ```bash
   USE_SQLITE=1 python manage.py createsuperuser
   ```

3. Запустите сервер разработки и откройте `http://127.0.0.1:8000/admin`.

   ```bash
   USE_SQLITE=1 python manage.py runserver 0.0.0.0:8000
   ```

### Роли и права

При первом запуске автоматически создаются группы:

- **Feed editors** — могут просматривать и изменять новости.
- **Feed moderators** — включают права редакторов + модерация (флаги, публикация, тональность) и запуск перевода.

Назначить роль можно стандартной командой shell:

```bash
USE_SQLITE=1 python manage.py shell -c "from django.contrib.auth import get_user_model; from django.contrib.auth.models import Group; User = get_user_model(); user = User.objects.get(username='editor'); user.groups.add(Group.objects.get(name='Feed editors'))"
```

### Быстрые действия и перевод

- В списке новостей доступны действия: публикация/снятие, пометка на проверку, изменение тональности, запуск перевода на русский.
- Перевод использует сервис из `apps.feed.services.translation`. Включить его можно переменной окружения `FEED_TRANSLATE_RU_ENABLED=1` и настройками:
  - `TRANSLATE_TARGET_LANG` — целевой язык (по умолчанию `ru`).
  - `TRANSLATE_PROVIDERS` — список провайдеров (поддерживается `yandex`).
  - `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` — креды Yandex Cloud Translate.

### Jazzmin

Если пакет `jazzmin` установлен, админка автоматически получает современный UI с быстрыми ссылками на разделы «Новости», «Рецепты», «Акции» и т.д. Без Jazzmin всё продолжит работать на стандартной теме Django.

### Часовой пояс

Админка использует часовой пояс `Europe/Moscow` (см. `TIME_ZONE` в настройках), поэтому даты и фильтры отображаются по московскому времени.

## Marketplace API

* Base path: `/api/v1/market/` (JWT required). All collection endpoints accept `page` and `page_size` (default 20, max 100) and return `count`, `page`, `page_size`, `next`, `previous`, and `results` payloads.
* Search: `?search=` applies case-insensitive filtering to human-readable fields (name/description/tags) across stores, products, and recipes.
* Ordering (`?ordering=`) aliases:
  * **Stores:** `name`, `rating` → JSON `metadata.rating`, `eta` → `metadata.delivery_eta_minutes`, `freshness` → `created_at`. Multiple fields can be comma-separated, prefixed with `-` for descending. Unsupported aliases yield HTTP 400 instead of 500.
  * **Products:** `title`, `price`, `discount` → `metadata.discount_percent`, `rating` → `metadata.rating`, `created` → `created_at`.
  * **Recipes:** `title`, `time_minutes` → `cooking_time_minutes`, `calories` → `metadata.nutrition.calories`, `rating` → `metadata.rating`, `price` → coalesced `metadata.price.value` / `metadata.price`, `created` → `created_at`.
* Filters:
  * **Stores:** `city`, `tag`, `max_eta`, `free_delivery`, `is_online`, `min_rating`.
  * **Products:** `store` (id or slug), `tag`, `origin`, `discount_only`, `available`, `min_price`, `max_price`, `published`, `min_rating`.
  * **Recipes:** `store`, `max_time`, `difficulty`, `tag`, `min_rating`, `min_protein`, `max_price` (supports number or JSON object with `value`).
* Serialization: responses expose flattened metadata — e.g. stores include `rating`, `delivery_eta_minutes`, `delivery_price`, `is_online`; products embed store snapshot, inventory availability, discount/original price, and badges; recipes expose macros (`calories`, `protein_g`, `fat_g`, `carbs_g`), pricing, flags (`is_premium`, `is_in_plan`), and nested `steps`/`ingredients`.
* SSE notifications are streamed from `/api/v1/market/events/` (Server-Sent Events). Subscribe with a valid access token and optional `resource` query to receive `market.{stores|products|recipes}` events containing `action` (`created`, `updated`, `status_changed`, etc.) and full entity payloads for real-time UI updates.
* Marketplace permissions: vendors manage their own stores/products; moderators (group `market_moderator`) moderate any payload. Non-operators only see active stores and public recipes.

## Marketplace demo data

Populate demo entities for local testing:

```bash
USE_SQLITE=1 python manage.py shell -c "from seeds import market; market.create()"
```

This command seeds a vendor store with a published product, recipe, inventory snapshot, sample cart and a meal plan owned by `demo-customer`.
