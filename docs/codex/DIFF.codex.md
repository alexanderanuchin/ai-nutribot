## 2025-11-03 – worktree (pending)

**Summary:** Surface real-time marketplace activity in the main feed and enrich SSE payload handling.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/types/market.ts | Expand realtime payload types to carry entity snapshots and metadata. | Frontend realtime | No |
| modify | frontend/src/features/market/hooks/useMarketEvents.ts | Allow multi-resource subscriptions and parse structured SSE payloads. | Frontend realtime | No |
| create | frontend/src/features/feed/components/MarketUpdatesPanel.tsx | Display incoming marketplace events as actionable feed highlights. | Frontend UX | No |
| modify | frontend/src/pages/Feed.tsx | Subscribe to marketplace SSE, manage update state, and render the new panel. | Frontend UX | No |
| modify | docs/frontend/market/market-events-contract.md | Document enriched payload structure for marketplace SSE consumers. | Frontend docs | No |

## 2025-11-01 – worktree (pending)

**Summary:** Marketplace query optimizations with supporting indexes and profiling harness.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | scripts/perf/market_benchmark.py | Add repeatable script to seed data and benchmark key market viewsets before/after optimizations. | Backend observability | No (uses existing runtime) |
| modify | backend/apps/market/models.py | Declare new B-tree indexes for frequent filters/orderings (city, price, cooking_time_minutes, user+updated_at). | Backend performance | Yes (market.0004) |
| create | backend/apps/market/migrations/0004_cart_market_cart_user_updated_desc_and_more.py | Schema migration creating the new ORM indexes. | Backend performance | Yes (apply migration) |
| modify | backend/apps/market/views.py | Reduce redundant prefetches and tighten queryset hints to cut SQL queries per request. | Backend performance | No |
| create | docs/codex/DIFF.codex.md | Document change set and benchmark impact. | Docs | No |

**Benchmark:** `scripts/perf/market_benchmark.py`

- Before: store 3q/5.46 ms, product 4q/16.19 ms, recipe 6q/34.14 ms, cart 3q/5.74 ms. Mean 15.38 ms.
- After: store 3q/5.63 ms, product 3q/10.79 ms, recipe 5q/33.02 ms, cart 2q/4.29 ms. Mean 13.43 ms.
## 2025-11-04 – worktree (pending)

**Summary:** Align marketplace API contracts with frontend filters/sorts and refresh documentation.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/types/market.ts | Sync marketplace entity types with serializer fields (slugs, metadata, nested steps/ingredients). | Frontend API | No |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Consume `cooking_time_minutes` and updated recipe snapshots in UI interactions. | Frontend UX | No |
| modify | frontend/src/features/market/cards/CardComponents.test.tsx | Refresh fixtures for expanded product/store/recipe contracts. | Frontend tests | No |
| modify | frontend/src/features/market/cards/RecipeCard.stories.tsx | Showcase story data using new recipe contract. | Frontend docs | No |
| modify | frontend/src/features/market/filters/config.ts | Centralise availability/price support per resource and disable unsupported sliders. | Frontend filters | No |
| modify | frontend/src/features/market/components/MarketFilters.tsx | Hide price/availability controls when backend does not support them. | Frontend UX | No |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Ensure pagination, ordering aliases, and filter params follow backend expectations. | Frontend API | No |
| modify | backend/README.md | Document marketplace filters, ordering aliases, and SSE usage. | Docs | No |

## 2025-11-04 – codex/frontend/sse-auth-refresh (pending)

**Summary:** Refresh JWTs before opening realtime channels and normalise SSE authentication failures away from 406 responses.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/common/renderers.py | Provide an SSE renderer that negotiates `text/event-stream` while serialising error payloads as UTF-8 JSON. | Backend realtime | No |
| modify | backend/apps/feed/views.py | Opt feed SSE into the event-stream renderer and keep permission failures consistent. | Backend realtime | No |
| modify | backend/apps/market/api/events.py | Use the SSE renderer and improve subscription bookkeeping for market events. | Backend realtime | No |
| modify | backend/apps/market/tests/test_events_api.py | Cover `text/event-stream` negotiation and expect 403 on unauthenticated access with JSON assertions. | Backend tests | No |
| create | frontend/src/utils/auth.ts | Add helper to ensure access tokens are refreshed before realtime connections. | Frontend auth | No |
| modify | frontend/src/features/market/hooks/useMarketEvents.ts | Refresh tokens before SSE connect/reconnect and harden cleanup. | Frontend realtime | No |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.ts | Refresh tokens prior to WebSocket/SSE negotiation and centralise transport cleanup. | Frontend realtime | No |
