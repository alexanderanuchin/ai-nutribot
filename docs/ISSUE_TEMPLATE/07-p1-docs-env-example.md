---
name: "P1 — Документация и `.env.example` для /market"
about: "Собрать переменные окружения и шаги запуска; описать ключевые эндпоинты /market."
title: "P1 — Документация и `.env.example` для /market"
labels: "P1,docs,devx"
assignees: ""
---
**Контекст**
Явного примера `.env` нет; запуск требует вытаскивать значения из `settings.py` и compose.

**Задачи**
- [ ] Создать `.env.example` (JWT, БД, CORS, Telegram init data и пр.).
- [ ] Обновить README с шагами запуска бэка/фронта и перечнем эндпоинтов /market.
- [ ] Указать поддерживаемые версии (Python/Django/Node/React).

**Критерии приёмки**
- [ ] Новый разработчик поднимает dev-окружение ≤ 15 минут по README.
- [ ] Фронт открывается и работает базовый happy-path списка.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
