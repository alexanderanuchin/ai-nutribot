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