# ADR 2025-11-08: Align marketplace cart/plan endpoints

- Status: Draft
- Deciders: Codex GPT (interim)
- Date: 2025-11-08

## Context

The frontend marketplace flows (`frontend/src/api/market.ts`, `frontend/src/features/market/`) call
`POST /v1/market/cart/` and `POST /v1/market/plan/` with simple payloads `{product_id, quantity}`
and `{recipe_id, servings}` respectively. The backend DRF router currently exposes
`/api/v1/market/cart-items/` and `/api/v1/market/meal-plan-items/` where payloads must include
`cart`/`meal_plan` foreign keys alongside nested relations (`backend/apps/market/urls.py`,
`backend/apps/market/serializers.py`). Because no convenience endpoints exist, the SPA mutations
return 404/400 responses and fall back to client-side Zustand state without persisting to the API.

This divergence was highlighted in issue template `docs/ISSUE_TEMPLATE/02-p0-cart-plan-routes.md` and
blocks checkout/plan UX as well as bot parity.

## Decision (pending)

Adopt Variant B from the template: add REST handlers under `/api/v1/market/cart/` and
`/api/v1/market/plan/` that authenticate the user, resolve or create the related cart/plan records,
and accept the simplified payloads expected by the frontend/bot clients. The handlers should return
idempotent upsert responses and continue to use the existing viewsets for underlying storage.

This ADR remains in draft until the implementation PR is prepared; it captures the preferred
direction for upcoming work and keeps Variant A (refactoring the SPA) as a fallback if backend scope
is constrained.

## Alternatives

1. **Variant A – Update SPA to use `cart-items` / `meal-plan-items`.** This would require Zustand
   stores to orchestrate cart/plan identifiers, fetching metadata before each mutation and passing
   foreign keys in the payload. It adds coupling between the client and backend schema and doubles
   API round trips for anonymous-to-authenticated transitions.
2. **Do nothing.** Leave cart/plan persistence disabled. This keeps the system inconsistent and makes
   `/market` add-to-cart buttons misleading.

## Consequences

- Backlog item opened to implement sugar endpoints that hide relational details from clients.
- Requires authentication middleware to derive `rid` and attach structured audit logs for each
  mutation so observability stays consistent with repository standards.
- The ADR should be revisited once the implementation is merged to update status from Draft to
  Accepted and document any deviations.
