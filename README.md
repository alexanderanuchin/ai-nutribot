# AI NutriBot

AI NutriBot - платформа питания с WebApp, Telegram-ботом и backend API.

Проект объединяет:

- **Backend**: Django 5, Django REST Framework, Channels, Celery, Redis, PostgreSQL/SQLite.
- **Frontend**: React 19, Vite, TypeScript, TanStack Query, Tailwind CSS.
- **Telegram bot**: aiogram 3, Telegram WebApp, профиль, кошелёк, планы питания, заказы и Stars-платежи.

Основные возможности: генерация планов питания, каталог и marketplace, заказы и кошелёк, Telegram-авторизация, новости/feed с импортом и переводом, отзывы, мониторинг, realtime-обновления через WebSocket и SSE.

## Структура

```text
backend/   Django-проект, REST API, Celery-задачи, admin, тесты
bot/       Telegram-бот
frontend/  Vite React WebApp
infra/     Docker Compose, Nginx, PgBouncer, ACME/SSL
docs/      Техническая документация и issue templates
scripts/   Вспомогательные скрипты
seeds/     Seed/demo-данные
```

## Требования

- Docker и Docker Compose для полного запуска.
- Python 3.12 для локальной разработки backend и bot.
- Node.js `>=20.19.0 <21` или `>=22.0.0` для frontend.

## Переменные окружения

Docker Compose читает `infra/.env`. Создайте этот файл перед запуском:

```env
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=dev-secret
JWT_SECRET=dev-jwt-secret

POSTGRES_DB=nutribot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=pgbouncer
POSTGRES_PORT=6432
REDIS_URL=redis://redis:6379/0

WEBAPP_URL=http://localhost:8080/
FRONTEND_URL=http://localhost:5173
DJANGO_CORS_ORIGINS=http://localhost:5173,http://localhost:8080
ALLOWED_HOSTS=localhost,127.0.0.1,backend

TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_KEY=dev-bot-key
TELEGRAM_BOT_USERNAME=CaloIQ_bot
BOT_USERNAME=CaloIQ_bot

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

FEED_TRANSLATE_RU_ENABLED=0
TRANSLATE_PROVIDERS=yandex
YANDEX_API_KEY=
YANDEX_FOLDER_ID=

CLOUDPUB_TOKEN=
```

Для production обязательно задайте стабильные секреты `DJANGO_SECRET_KEY`, `JWT_SECRET`, `TELEGRAM_BOT_KEY`, реальные хосты, CORS origins, Telegram-токены, настройки БД и платежного провайдера.

## Запуск через Docker

Из корня репозитория:

```bash
cd infra
docker compose up --build
```

Основные адреса:

- WebApp через Nginx: `http://localhost:8080`
- Vite dev server: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Django admin: `http://localhost:8000/admin/`
- Health: `http://localhost:8000/healthz`, `http://localhost:8000/readyz`
- Metrics: `http://localhost:8000/metrics`

Стек Compose поднимает PostgreSQL, PgBouncer, Redis, backend, Celery worker, Celery Beat, Telegram-бота, frontend, Nginx gateway, certbot helpers и CloudPub agent.

## Локальный backend

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

USE_SQLITE=1 DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret python manage.py migrate
USE_SQLITE=1 DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret python manage.py load_seeds
USE_SQLITE=1 DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret uvicorn nutribot.asgi:application --host 0.0.0.0 --port 8000 --reload
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:USE_SQLITE="1"
$env:DJANGO_DEBUG="1"
$env:DJANGO_SECRET_KEY="dev-secret"
python manage.py migrate
python manage.py load_seeds
uvicorn nutribot.asgi:application --host 0.0.0.0 --port 8000 --reload
```

Celery worker для async-задач планов питания и feed:

```bash
cd backend
USE_SQLITE=1 DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret celery -A nutribot worker -l info -Q default,feed.ingestion,nutrition,celery
```

## Локальный frontend

```bash
cd frontend
npm install
npm run dev
```

Опциональные переменные frontend:

```env
VITE_API_BASE=/api
VITE_WS_BASE=
VITE_APP_BASE_PATH=/
VITE_TELEGRAM_BOT_USERNAME=CaloIQ_bot
VITE_DEBUG_LOGS=0
```

## Локальный Telegram-бот

Linux/macOS:

```bash
cd bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

TELEGRAM_BOT_TOKEN=... \
TELEGRAM_BOT_KEY=dev-bot-key \
BACKEND_BASE_URL=http://localhost:8000 \
WEBAPP_URL=http://localhost:5173/ \
python -m bot.app
```

Для webhook-режима задайте `WEBHOOK_ENABLE=1`, `WEBHOOK_URL`, при необходимости `WEBHOOK_SECRET`, `WEBHOOK_PORT` и `WEBHOOK_PATH`.

## API

- `POST /api/auth/...` - авторизация и JWT refresh.
- `/api/users/...` - профили, Telegram-интеграция, bridge-сессии.
- `/api/catalog/...` - каталог и блюда.
- `/api/nutrition/...` - планы питания.
- `/api/orders/...` - кошелёк, заказы и платежи.
- `/api/reviews/...` - отзывы.
- `/api/monitoring/...` - логи приложения и мониторинг.
- `/api/v1/...` - feed API.
- `/api/v1/market/...` - marketplace API, корзина, meal plans и SSE events.

## Данные и импорты

Seed-данные:

```bash
cd backend
USE_SQLITE=1 python manage.py load_seeds
USE_SQLITE=1 python manage.py shell -c "from seeds import market; market.create()"
```

Импорт USDA-каталога:

```bash
cd backend
USE_SQLITE=1 python manage.py sync_usda_catalog --limit 150 --min-calories 180
```

Импорт feed-источников:

```bash
cd backend
python manage.py ingest_feed_sources --limit-per-source=5
```

## Тесты и качество

Backend:

```bash
cd backend
pytest
```

Bot:

```bash
cd bot
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

Mypy-проверка из корня репозитория:

```bash
make typecheck
```

## Важные заметки

- Backend-тесты локально по умолчанию используют SQLite через `backend/conftest.py`.
- `JWT_SECRET` должен быть стабильным между рестартами, иначе выданные access/refresh-токены станут невалидными.
- `TELEGRAM_BOT_KEY` должен совпадать в backend и bot: им бот подписывает внутренние запросы к backend.
- `OPENAI_API_KEY` включает LLM-планировщик питания; без ключа используются fallback-эвристики там, где они реализованы.
- Перевод feed работает через Yandex-настройки при `FEED_TRANSLATE_RU_ENABLED=1`.
- Production-трафик рассчитан на Nginx из `infra/nginx.conf`: он проксирует `/api/`, `/ws/`, SSE endpoints, frontend и Telegram webhook.
