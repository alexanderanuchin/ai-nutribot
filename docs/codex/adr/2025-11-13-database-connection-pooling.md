# ADR: Database connection pooling and admin log throttling

## Контекст

В проде и staging админка NutriBot транслирует живой поток `/admin/monitoring/applicationlog/stream/`.
Каждая вкладка инициирует новые HTTP-запросы к Django, а драйвер `django_prometheus.db.backends.postgresql`
открывает отдельные соединения к PostgreSQL. Без пула и `CONN_MAX_AGE` эти коннекты не переиспользуются.
Нагрузка усиливается Celery-воркерами и SSE-потоками маркетплейса, поэтому Postgres упёрся в лимит
`max_connections`, сессии стали отваливаться и аутентификация не читала `request.session`.

## Решение

1. Добавить PgBouncer (transaction pooling) между приложениями и Postgres в `docker-compose.yml`,
   использовать поддерживаемый образ `edoburu/pgbouncer:v1.24.1-p1`, хранить конфигурацию в `infra/pgbouncer/`
   и направлять Django/Celery через порт 6432.
2. В Django прописать `CONN_MAX_AGE=0`, `CONN_HEALTH_CHECKS`, `DISABLE_SERVER_SIDE_CURSORS`, защитные таймауты
   и вынести сессии в Redis-кеш (или `LocMem` в тестах), чтобы админка не держала БД-коннекты ради cookies.
3. Ограничить gunicorn/worker-пулы через переменные `WEB_WORKERS`, `WEB_THREADS`, `CELERY_WORKER_CONCURRENCY`,
   чтобы инстансы не открывали десятки соединений одновременно.
4. Разгрузить `/admin/monitoring/applicationlog/stream/`: `transaction.non_atomic_requests`, ручное закрытие
   соединений, новый селектор интервала (5–60с) и автообновление в паузе по умолчанию.
5. SSE в маркетплейсе (`/api/v1/market/events/`) тоже выполняется вне транзакций и закрывает коннекты перед
   долгим стримингом.

## Альтернативы

- **Просто поднять `max_connections`.** Быстрое решение, но Postgres упрётся в память/контекстные переключения,
  а причина (шторм коннектов) останется.
- **Встроенный пул Django (`CONN_MAX_AGE>0`).** При 20+ воркерах это всё равно приведёт к сотням коннектов и не
  защитит от Celery/SSE. PgBouncer даёт жёсткий лимит и переиспользование.
- **Отключить поток логов.** Упростит ситуацию, но команда админки лишится реального мониторинга. Мы лишь
  перевели его в более щадящий режим.

## Последствия

- Compose получает новый сервис `pgbouncer`; деплой/локальные окружения должны прогонять `docker compose up`
  с дополнительным контейнером.
- Django теперь зависит от Redis для продовых сессий (в dev/tests падает на `LocMem`). Надо держать Redis живым.
- Настроенные таймауты (`statement_timeout`, `idle_in_transaction_session_timeout`) влияют на долгие SQL;
  бизнес-код должен обрабатывать `OperationalError` и ретраи.
- Автообновление логов медленнее: админам нужно вручную возобновлять поток, но зато Postgres перестаёт
  упираться в лимит.
