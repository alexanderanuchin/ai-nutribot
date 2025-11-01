---
name: "P0 — Realtime: добавить `/api/v1/market/events/` (SSE)"
about: "Фронт слушает `/api/v1/market/events/`, такого эндпоинта нет; нужен прокси на feed или отдельный источник."
title: "P0 — Realtime: добавить `/api/v1/market/events/` (SSE)"
labels: "P0,backend,api,realtime"
assignees: ""
---
**Контекст**
Фронт открывает SSE на `/api/v1/market/events/`, бэкенд предоставляет только `/api/v1/feed/events/`. Из-за этого — постоянные 404 и не работает FreshBanner.

**Решение (временное)**
Сделать `/api/v1/market/events/` прокси к `/api/v1/feed/events/` с фильтрами `topic=market.*`. Аутентификация — JWT.

**Задачи**
- [ ] Реализовать endpoint-прокси `/api/v1/market/events/`.
- [ ] Ограничить топики группой `market.*` (без лишних потоков).
- [ ] Обновить документацию контракта.
- [ ] Нагрузочное sanity-тестирование (час непрерывного соединения).

**Критерии приёмки**
- [ ] Фронт устанавливает и удерживает SSE-соединение ≥ 1 часа.
- [ ] FreshBanner/автообновление срабатывают по событию.
- [ ] 404 на `/market/events/` исчезли из логов.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
