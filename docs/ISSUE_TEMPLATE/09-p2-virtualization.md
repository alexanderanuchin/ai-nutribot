---
name: "P2 — Виртуализация списков"
about: "Стабильный FPS и снижение затрат при длинных коллекциях."
title: "P2 — Виртуализация списков"
labels: "P2,frontend,perf,ux"
assignees: ""
---
**Контекст**
Сейчас IntersectionObserver + skeleton, но без виртуализации.

**Задачи**
- [ ] Включить виртуальный список для коллекций /market.
- [ ] Сохранить поведение дозагрузки по достижению конца.

**Критерии приёмки**
- [ ] При 500+ карточек скролл остаётся плавным; потребление памяти умеренное.

**Связанные материалы**
- Раздел /market (frontend): `frontend/src/pages/market/`, `frontend/src/features/market/`
- Типы и API-обёртки фронта: `frontend/src/types/market.ts`, `frontend/src/api/market.ts`
- Бэкенд /market: `backend/apps/market/` (models, serializers, views, urls, services, pagination)
- Поиск: `backend/apps/market/services/search.py`
