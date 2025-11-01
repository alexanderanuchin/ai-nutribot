---
name: "P0 — Cart/Plan: выровнять маршруты и payload"
about: "Фронт и API расходятся в URL и теле запросов для корзины/плана питания."
title: "P0 — Cart/Plan: выровнять маршруты и payload"
labels: "P0,frontend,backend,api"
assignees: ""
---
**Контекст**
Фронт шлёт `POST /v1/market/cart/ {product_id, quantity}` и `POST /v1/market/plan/ {recipe_id, servings}`. Бэкенд предоставляет `/cart-items/` и `/meal-plan-items/` и ожидает `cart`/`meal_plan` (FK) в payload.

**Варианты решения**
- Вариант A (быстро): переключить фронт на существующие ручки `/cart-items/` и `/meal-plan-items/` с требуемым payload.
- Вариант B (удобно для фронта): добавить на бэке сахарные ручки `/cart/` и `/plan/` с простым payload, маппящиеся на сущности.

**Задачи**
- [ ] Выбрать вариант A/B и зафиксировать контракт.
- [ ] Реализовать изменения (фронт/бэк).
- [ ] Обновить адаптеры и типы; починить disabled-состояния кнопок.
- [ ] Написать тест(ы) на happy/validation path.

**Критерии приёмки**
- [ ] Товар/рецепт успешно добавляется в корзину/план со страницы списка.
- [ ] Ошибки валидации дают понятные сообщения.
- [ ] Состояние Zustand стора синхронизируется без рассинхронов.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
