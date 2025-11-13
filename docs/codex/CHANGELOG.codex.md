## 2025-11-25 – Feed websocket origin tolerance (pending)

- Let Channels accept `/ws/feed` whether or not a proxy strips the leading slash and
  covered the authenticated handshake with a stubbed communicator test so we stop
  logging three failed upgrade attempts before falling back to SSE. See
  [DIFF 2025-11-25](./DIFF.codex.md#2025-11-25--codexbackendfeed-ws-origin-pending).

## 2025-11-24 – Feed realtime websocket routing (pending)

- Updated the Channels routing to accept `/ws/feed` alongside `/ws/feed/` and
  added communicator tests so authenticated clients stop hitting Django's 404
  handler before reconnecting via SSE. See
  [DIFF 2025-11-24](./DIFF.codex.md#2025-11-24--codexbackendfeed-ws-routing-pending).

## 2025-11-24 – Feed realtime base resolvers (pending)

- Adjusted realtime base resolver tests to cover WebSocket and HTTP fallbacks,
  and asserted the feed realtime hook now dials `wss://<host>/ws/...` so local
  runs stop expecting the legacy `/api` suffix. See
  [DIFF 2025-11-24](./DIFF.codex.md#2025-11-24--codexfrontendfeed-realtime-bases-pending).

## 2025-11-24 – Feed realtime proxy hardening (pending)

- Proxied /ws/ traffic through Nginx so feed realtime clients can establish WebSocket connections and added unbuffered SSE passthrough to avoid SSL protocol errors when falling back. See [DIFF 2025-11-24](./DIFF.codex.md#2025-11-24--codexinfrafeed-ws-proxy-pending).

## 2025-11-12 – Marketplace SSE formatter adapter (pending)

- Wrapped marketplace SSE formatting with a byte-normalising adapter and regression tests so mixed
  formatter outputs no longer corrupt the stream over HTTP/2. See
  [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexbackendmarket-sse-byte-adapter-pending).

## 2025-11-23 – Feed realtime WebSocket cleanup (pending)

- Deferred closing CONNECTING feed sockets until after the `open` event to silence Chrome
  "connection closed" noise and refreshed realtime tests with richer mocks. See
  [DIFF 2025-11-23](./DIFF.codex.md#2025-11-23--codexfrontendfeed-realtime-ws-cleanup-pending).

## 2025-11-12 – Marketplace SSE renderer hardening (pending)

- Added a DRF event-stream renderer, stricter validation, and removed hop-by-hop headers so
  `/api/v1/market/events/` stays compatible with EventSource clients without 406/500 errors. See
  [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexbackendmarket-sse-renderer-pending).

## 2025-11-20 – Marketplace cart integration (pending)

- Shared checkout logic and cart summaries across marketplace pages so programs support full purchases and the mobile cart bar clears the tab bar. See [DIFF 2025-11-20](./DIFF.codex.md#2025-11-20--codexfrontendmarket-cart-integration-pending).

## 2025-11-18 – Backend typing bootstrap (pending)

- Wired mypy with Django/DRF stubs, annotated hot-path services, and exposed a `make typecheck`
  target for reproducible checks. See [DIFF 2025-11-18](./DIFF.codex.md#2025-11-18--codexinframypy-bootstrap-pending).

## 2025-11-17 – Lint/style standardisation (pending)

- Adopted shared Ruff excludes plus React-aware ESLint and Prettier configs for consistent
formatting. See [DIFF 2025-11-17](./DIFF.codex.md#2025-11-17--codexinfralint-style-pending).

## 2025-11-16 – Continuous integration workflow (pending)

- Added GitHub Actions CI covering security audits, linting, and frontend testing with caching on Python 3.12 and Node 22. See [DIFF 2025-11-16](./DIFF.codex.md#2025-11-16--codexinfraci-workflow-pending).

## 2025-11-09 – Dependency security refresh (pending)

- Regenerated Python lock files and raised the frontend toolchain (Vite 6.4 + Vitest 4) to clear pip/npm audits. See [DIFF 2025-11-09](./DIFF.codex.md#2025-11-09--codexsecuritydependency-refresh-pending).

## 2025-11-15 – Container hardening (pending)

- Hardened backend, bot, and frontend containers with multi-stage builds, non-root execution, and health probes, and refined backend health/migration bootstrap for stability. See [DIFF 2025-11-15](./DIFF.codex.md#2025-11-15--codexinfracontainer-hardening-pending).

## 2025-11-08 – Security & quality audit baseline (pending)

- Published `CODEX_AUDIT_REPORT.md` and captured actionable findings. See [DIFF 2025-11-08](./DIFF.codex.md#2025-11-08--codexdocsfull-audit-pending).

## 2025-11-14 – Marketplace meal plan polish (pending)

- Refined marketplace programs hub placement and responsive filters on the meal plan listing. See [DIFF 2025-11-14](./DIFF.codex.md#2025-11-14--codexfrontendmarket-mealplans-polish-pending).

## 2025-11-13 – Marketplace meal plan programs (pending)

- Added goal/tag metadata, nutrition metrics, and SPA listing/detail pages for marketplace meal plans. See [DIFF 2025-11-13](./DIFF.codex.md#2025-11-13--codexfullstackmarket-mealplan-programs-pending).

## 2025-11-12 – Premium marketplace monetisation (pending)

- Added wallet-backed purchase flows for marketplace recipes and meal plans, granting access via RecipeAccess/MealPlanAccess models and exposing Star pricing in API responses. See [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexfullstackmarket-premium-pending).

## 2025-11-12 – React Router v7 upgrade (pending)

- Raised the SPA routing stack to React Router v7 and normalised nested market paths ahead of v7's relative splat defaults. See [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexfrontendreact-router-v7-pending).
