---
name: "P1 — Индексы и выборки (price/origin/delivery_eta + select_related)"
about: "Ускорить фильтры/сортировки за счёт индексов и устранить N+1 в витрине."
title: "P1 — Индексы и выборки (price/origin/delivery_eta + select_related)"
labels: "P1,backend,perf,database"
assignees: ""
---
**Контекст**
Часть фильтров/сортировок потенциально медленные (price, metadata->origin/eta). В местах есть риск N+1.

**Задачи**
- [ ] Добавить индексы для `price`, `metadata->origin`, `metadata->delivery_eta_minutes`.
- [ ] Ревизия `select_related/prefetch_related` для Stores/Products/Recipes.
- [ ] Мини-бенчмарк до/после на dev-данных.

**Критерии приёмки**
- [ ] p95 API-листингов ≤ 300 мс на dev-данных.
- [ ] Логи не содержат N+1 для витринных запросов.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
