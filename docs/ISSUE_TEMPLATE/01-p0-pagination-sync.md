---
name: "P0 — Pagination: временный переход на page/page_size"
about: "Разблокировать бесконечную прокрутку: фронт временно переходит на page/page_size до внедрения курсоров."
title: "P0 — Pagination: временный переход на page/page_size"
labels: "P0,frontend,backend,api"
assignees: ""
---
**Контекст**
Сейчас фронт ожидает `cursor`, а API возвращает `page/page_size`. Это ломает дозагрузку (первая страница повторяется/не грузится).

**Задачи**
- [ ] Обновить `fetchMarketCollection` на использование `page`/`page_size` и полей ответа `count/next/previous/results`.
- [ ] Привести типы/адаптеры данных под новую схему ответа.
- [ ] Убедиться, что infinite scroll корректно запрашивает следующую страницу и не дублирует карточки.
- [ ] Обновить тесты (если есть) или добавить минимальные.

**Критерии приёмки**
- [ ] Дозагрузка следующей страницы работает стабильно на всех коллекциях (products/stores/recipes).
- [ ] Нет повторов/«залипаний» на первой странице.
- [ ] Время ответа и плавность скролла не ухудшились.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
