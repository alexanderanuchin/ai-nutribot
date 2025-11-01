---
name: "P0 — Summary поля: отдать плоские поля в коллекциях"
about: "Карточки витрины требуют плоские поля (price/available/rating/и т.д.) без распаковки nested metadata/inventory на фронте."
title: "P0 — Summary поля: отдать плоские поля в коллекциях"
labels: "P0,backend,api,frontend"
assignees: ""
---
**Контекст**
Фронт ожидает плоские поля для карточек; сейчас данные частично лежат в `inventory`/`metadata`, из-за чего кнопки отключены и видны `NaN`.

**Задачи**
- [ ] Для `Product` добавить: `available`, `price`, `price_original`, `discount_percent`, `image_url`, `brand`.
- [ ] Для `Recipe` добавить: `calories`, `protein_g`, `fat_g`, `carbs_g`, `price`, `rating`.
- [ ] Для `Store` добавить: `rating`, `delivery_eta_minutes`, `hero_image_url`.
- [ ] Использовать `select_related/prefetch_related` для эффективности.
- [ ] Обновить фронтовые типы/рендер карточек.

**Критерии приёмки**
- [ ] Карточки полностью заполнены; нет `NaN`; кнопки активны при `available=true`.
- [ ] Рендер карточек не деградировал по времени.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
