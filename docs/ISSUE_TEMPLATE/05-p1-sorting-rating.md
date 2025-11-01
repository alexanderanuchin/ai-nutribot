---
name: "P1 — Сортировки, рейтинги и белок/цена для рецептов"
about: "Добавить OrderingFilter, `min_rating`, поддержку `min_protein` и `max_price` в поиске/листингах."
title: "P1 — Сортировки, рейтинги и белок/цена для рецептов"
labels: "P1,backend,api,frontend,perf"
assignees: ""
---
**Контекст**
Фронт отправляет `ordering`, `min_rating`, `min_protein`, `max_price`, но API игнорирует часть параметров.

**Задачи**
- [ ] Подключить `OrderingFilter` и явно разрешённые поля (`-rating`, `price`, `-discount_percent`, и т.д.).
- [ ] Реализовать обработку `min_rating`.
- [ ] Для рецептов — поддержать `min_protein`, `max_price` (по агрегированным полям).
- [ ] Обновить спецификацию и фронт (список сортировок/фильтров).

**Критерии приёмки**
- [ ] Изменение сортировки на фронте перестраивает список на бэке.
- [ ] Фильтры `min_rating`, `min_protein`, `max_price` реально сужают выдачу.
- [ ] Появились индексы/оптимизации при необходимости.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
