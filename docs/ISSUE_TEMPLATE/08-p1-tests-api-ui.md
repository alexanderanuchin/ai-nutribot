---
name: "P1 — Тесты API и UI для /market (минимум)"
about: "Покрыть критические сценарии: листинги, фильтры, пагинация, добавление в корзину/план, поиск."
title: "P1 — Тесты API и UI для /market (минимум)"
labels: "P1,qa,backend,frontend"
assignees: ""
---
**Контекст**
API покрыто слабо; фронт-интеграция не тестируется.

**Задачи**
- [ ] API-тесты: products/stores/recipes (успех, валидация, пусто, ошибка), pagination, search, cart/plan.
- [ ] UI-тесты: карточки (enabled/disabled), пагинация, обработка ошибок; e2e (Cypress/Playwright) — happy-path корзины.
- [ ] Интеграционные тесты для контрактов (типов данных).

**Критерии приёмки**
- [ ] Все критические сценарии зелёные на CI.
- [ ] Регресс P0 ловится тестами.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
