---
name: "P2 — ETag/Conditional GET для коллекций и поиска"
about: "Снизить трафик и ускорить повторные загрузки."
title: "P2 — ETag/Conditional GET для коллекций и поиска"
labels: "P2,backend,api,perf"
assignees: ""
---
**Контекст**
Повторные запросы сейчас всегда полные; нет 304.

**Задачи**
- [ ] Включить генерацию ETag/Last-Modified для списков/поиска.
- [ ] На фронте отправлять If-None-Match/If-Modified-Since для повторных запросов.
- [ ] Описать поведение в документации.

**Критерии приёмки**
- [ ] Повторные запросы отдают 304 там, где данные не менялись.
- [ ] Снижен трафик и время ответа при навигации назад/вперёд.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
