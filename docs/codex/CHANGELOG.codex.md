## 2025-12-22 – Telegram WebApp confirmation flags (pending)

- Gated Mini App auth confirmations behind explicit flags, collected initData from header/body/query sources, ensured the bot
  receives auth payloads via sendData (with legacy/current token keys and a brief delivery cushion) before any optional
  WebView close, and returned JWTs to the WebApp exchange response so sendData always carries tokens. See
  [DIFF 2025-12-22](./DIFF.codex.md#2025-12-22--codexfullstacktelegram-webapp-confirm-flag-pending).

## 2025-12-21 – Mini App auth runtime stability (pending)

- Allowed the Telegram Mini App auth bridge to keep the WebView open on desktop clients and accept backend logins that omit
  access/refresh tokens, aligning the SPA with the server-side token store. See
  [DIFF 2025-12-21](./DIFF.codex.md#2025-12-21--codexfrontendtelegram-auth-runtime-stability-pending).

## 2025-11-18 – Telegram WebApp auth flow hardening (pending)

- Made Telegram WebApp confirmations opt-in to avoid auto-closing, gathered initData from header/body/query/hash sources, and
  resumed sending auth tokens to the bot via `sendData` before optionally closing the WebView. See
  [DIFF 2025-11-18](./DIFF.codex.md#2025-11-18--codexfullstacktelegram-webapp-flow-pending).

## 2025-12-10 – Bot auth bridge buttons (pending)

- Updated bot auth prompts to launch the `/auth-bridge` Mini App via `web_app`
  buttons (reply and inline) so Telegram clients pass `initData`; added focused
  tests for the shared bridge URL builder and profile auth markup. See
  [DIFF 2025-12-10](./DIFF.codex.md#2025-12-10--codexbotwebapp-auth-bridge-buttons-pending).

## 2025-11-16 – Telegram integration surface (pending)

- Added the `/profile/integrations/telegram` experience with hero/status cards, deep-link + QR helpers, and a lightweight
  chat shell that streams server-side bridge events. Backend now issues/records start/startapp payloads, exposes status + bridge
  endpoints, and accepts JWT via query for SSE. See
  [DIFF 2025-11-16](./DIFF.codex.md#2025-11-16--codexfrontendtelegram-integration-pending).

## 2025-12-07 – Telegram Mini App auth bridge (pending)

- Added the WebApp auth bridge flow: reply-keyboard CTA opens `/auth-bridge`,
  the Mini App boots auth, sends a compact `sendData` payload with rid/reason,
  and closes instantly; bot logs `web_app_data` receipt and stores tokens with
  a confirmation message. Added guarded auto-rehydrate, MainButton fallback,
  and telemetry for sendData/login/init-data gaps. Follow-up refined
  sendData payload fields/diagnostics and fixed Telegram API imports. See
  [DIFF 2025-12-07](./DIFF.codex.md#2025-12-07--codexwebapp-auth-bridge-pending).

## 2025-12-07 – Telegram rehydrate hardening (pending)

- Guarded the auto-rehydrate sendData so it fires once per load with fresh
  tokens, removed reply keyboards after successful auth confirmation, and
  expanded bot WebApp-data tests for exp/exp_at variants and invalid payloads.
  See [DIFF 2025-12-07](./DIFF.codex.md#2025-12-07--codexfullstacktelegram-rehydrate-pending).

## 2025-12-04 – Stage 3 Stars monetization (bot) (pending)

- Finalised the Stage 3 Stars flow in the Telegram bot: added plan-specific
  top-up UX, symmetric audit logging for holds/job outcomes, enriched
  insufficient balance and region-block messaging, and exercised the resume
  paths/job-release fallbacks in tests. See
  [DIFF 2025-12-04](./DIFF.codex.md#2025-12-04--codexbotstars-monetization-stage3-end-pending).

## 2025-12-04 – Bot Stars monetization (pending)

- Enabled the Telegram bot to price, reserve, and consume Stars directly via
  the backend wallet APIs with idempotent holds and automatic resume after
  top-ups, alongside comprehensive tests for the new flows. See
  [DIFF 2025-12-04](./DIFF.codex.md#2025-12-04--codexbotstars-monetization-pending).
- Completed the Telegram Payments wiring end to end: provider token env
  plumbing for bot/backend, invoice payload metadata (`intent`/`aid`/`action`),
  attempt-tracked resumes, and consistent Stars block fallbacks across bot
  entry points. See
  [DIFF 2025-12-04](./DIFF.codex.md#2025-12-04--codexbotstars-monetization-pending).
- Introduced plan-specific top-up UX, deterministic hold idempotency/context
  logging, shared Stars invoice helpers, and documented the server-side pricing
  environment defaults. See
  [DIFF 2025-12-04](./DIFF.codex.md#2025-12-04--codexbotstars-monetization-pending).

## 2025-12-03 – Bot Stage 2 launcher (pending)

- Brought the Telegram bot start flow to the Stage 2 spec: hero card with the
  compact inline launcher, Info & Legal hub, wallet login prompt refresh, and
  chat menu WebApp shortcut. See
  [DIFF 2025-12-03](./DIFF.codex.md#2025-12-03--codexbotstage2-launcher-pending).

## 2025-12-02 – Bot Stage 1 bootstrap (pending)

- Standardised the Telegram bot bootstrap: new `bot.main` entrypoint, unified
  logging via `logkit`, redis/env plumbing in `Config`, and the minimalist
  inline `/start` launcher with legal/support links driven by env vars. See
  [DIFF 2025-12-02](./DIFF.codex.md#2025-12-02--codexbotstage1-bootstrap-pending).

## 2025-12-01 – Admin static asset hardening (pending)

- Added WhiteNoise-backed static serving, container `collectstatic`, and locked
  dependencies so the Django admin regains styles/scripts when running behind
  Gunicorn. See
  [DIFF 2025-12-01](./DIFF.codex.md#2025-12-01--codexbackendadmin-static-assets-pending).

## 2025-11-30 – Feed websocket ASGI dev server (pending)

- Swapped the Docker Compose dev backend to Uvicorn and documented the ASGI
  startup so `/ws/feed` handshakes reach Channels instead of Django's WSGI
  handler, and stretched the Nginx `/ws/` proxy timeouts to keep idle
  connections alive behind CloudPub. See
  [DIFF 2025-11-30](./DIFF.codex.md#2025-11-30--codexinfrafeed-ws-asgi-pending).

## 2025-11-29 – Feed realtime handshake fallback (pending)

- Dial WebSocket retries back to a single attempt when the handshake never
  opens, letting the feed hook fall back to SSE immediately while keeping
  reconnects for sockets that previously connected. See
  [DIFF 2025-11-29](./DIFF.codex.md#2025-11-29--codexfrontendfeed-realtime-handshake-pending).

## 2025-11-28 – Dual CloudPub/Caloiq domains (pending)

- Trusted Caloiq wildcard origins alongside CloudPub defaults so backend CSRF/CORS checks
  and the frontend dev proxy (including the apex `caloiq.ru` host) work without retuning
  env vars during the switchover. See
  [DIFF 2025-11-28](./DIFF.codex.md#2025-11-28--codexinfra-multi-domain-pending).

## 2025-11-27 – Feed manual refresh resilience (pending)

- Prevent manual feed refresh CTA from being locked by realtime refetches and document the change in the DIFF ledger. See [DIFF 2025-11-27](./DIFF.codex.md#2025-11-27--codexfrontendfeed-manual-refresh-pending).

## 2025-11-26 – Feed websocket allowed hosts (pending)

- Enriched backend allowed hosts with origins from `DJANGO_CORS_ORIGINS`/`WEBAPP_URL`
  so Channels accepts CloudPub WebSocket upgrades instead of forcing the SSE
  fallback, keeping the legacy `_parse_allowed_hosts` helper signature intact by
  layering a new `_extend_allowed_hosts` step. See
  [DIFF 2025-11-26](./DIFF.codex.md#2025-11-26--codexbackendfeed-ws-allowed-hosts-pending).

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

## 2025-11-13 – Database connection pooling hardening (pending)

- Added PgBouncer to the compose stack, tuned Django gunicorn/Celery worker limits,
  moved sessions to Redis cache, slowed the admin console poll interval, and
  pinned the compose service to the supported `edoburu/pgbouncer:v1.24.1-p1` image so
  PostgreSQL no longer saturates its connection cap and Docker builds stay green.
  See
  [DIFF 2025-11-13](./DIFF.codex.md#2025-11-13--codexinfradatabase-connection-pooling-pending).

## 2025-11-14 – Marketplace meal plan polish (pending)

- Refined marketplace programs hub placement and responsive filters on the meal plan listing. See [DIFF 2025-11-14](./DIFF.codex.md#2025-11-14--codexfrontendmarket-mealplans-polish-pending).

## 2025-11-13 – Marketplace meal plan programs (pending)

- Added goal/tag metadata, nutrition metrics, and SPA listing/detail pages for marketplace meal plans. See [DIFF 2025-11-13](./DIFF.codex.md#2025-11-13--codexfullstackmarket-mealplan-programs-pending).

## 2025-11-12 – Premium marketplace monetisation (pending)

- Added wallet-backed purchase flows for marketplace recipes and meal plans, granting access via RecipeAccess/MealPlanAccess models and exposing Star pricing in API responses. See [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexfullstackmarket-premium-pending).

## 2025-11-12 – React Router v7 upgrade (pending)

- Raised the SPA routing stack to React Router v7 and normalised nested market paths ahead of v7's relative splat defaults. See [DIFF 2025-11-12](./DIFF.codex.md#2025-11-12--codexfrontendreact-router-v7-pending).
## 2025-12-05 – WebApp base path routing (pending)

- Taught the SPA to respect `WEBAPP_URL` sub-paths by exporting a shared
  base-path helper, wiring the inferred basename into `BrowserRouter`, and
  covering the sanitisation logic with unit tests. See
  [DIFF 2025-12-05](./DIFF.codex.md#2025-12-05--codexfrontendwebapp-base-path-pending).

## 2025-12-06 – WebApp multi-domain parsing (pending)

- Normalised `WEBAPP_URL` list handling so the bot and SPA pick a single HTTPS
  candidate, keeping Telegram keyboards and router basenames aligned when
  multiple domains are configured. See
  [DIFF 2025-12-06](./DIFF.codex.md#2025-12-06--codexfullstackwebapp-multi-url-pending).


## 2025-12-09 – Telegram integration UI polish (pending)

- Refined the Telegram integration page with skeleton placeholders, accessibility labels, toast feedback, and richer diagnostics
  (including last sendData RID) for deep-link onboarding. See
  [DIFF 2025-12-09](./DIFF.codex.md#2025-12-09--codexfullstacktelegram-ui-diagnostics-pending).

## 2025-12-10 – Telegram bridge SSE hardening (pending)

- Wired Redis-backed pub/sub for the Telegram chat bridge, rate-limited the bridge send endpoint, mirrored bot updates into the
  SSE channel, and taught the chat shell to reconnect streams with smooth scrolling. See
  [DIFF 2025-12-10](./DIFF.codex.md#2025-12-10--codexfullstacktelegram-bridge-sse-pending).

## 2025-12-11 – Telegram bridge compatibility (pending)

- Made the Telegram bridge tolerant of missing Redis/httpx/logging helpers, reused user-level telegram_id fallbacks, and ensured
  Mini App payload decode errors are handled gracefully. See
  [DIFF 2025-12-11](./DIFF.codex.md#2025-12-11--codexbackendtelegram-bridge-compat-pending).

## 2025-12-12 – Telegram chat bridge documentation (pending)

- Clarified SSE token-in-query trade-offs for the Telegram chat bridge, added logging guidance, and aligned status payloads and
  UI labels around app vs Telegram usernames. See
  [DIFF 2025-12-12](./DIFF.codex.md#2025-12-12--codexfullstacktelegram-bridge-docs-pending).

## 2025-12-13 – WebApp URL path alignment (pending)

- Updated the default `WEBAPP_URL` to include `/auth-bridge`, ensuring Mini App launches in Telegram supply initData for
  auto-auth flows. See
  [DIFF 2025-12-13](./DIFF.codex.md#2025-12-13--codexinfrawebapp-url-path-pending).

## 2025-12-14 – Telegram startapp vs WebApp URL (pending)

- Separated startapp deeplinks from the WebApp URL, pushing the bot username into the frontend and forcing CTAs/auth buttons to
  open the Mini App context. See
  [DIFF 2025-12-14](./DIFF.codex.md#2025-12-14--codexfullstacktelegram-startapp-link-pending).

## 2025-12-15 – Mini App runtime-gated auth bridge (pending)

- Added strict Mini App runtime detection and a reusable auth bridge so Telegram CTAs exchange initData for JWTs only when
  inside the WebApp context, falling back to startapp deeplinks otherwise. See
  [DIFF 2025-12-15](./DIFF.codex.md#2025-12-15--codexfullstacktelegram-runtime-auth-bridge-pending).

## 2025-12-16 – Telegram deeplink signature compatibility (pending)

- Restored backward compatibility for Telegram start/startapp deeplink builders so legacy call signatures don't swap payloads
  and bot usernames. See
  [DIFF 2025-12-16](./DIFF.codex.md#2025-12-16--codexfullstacktelegram-deeplink-compat-pending).

## 2025-12-19 – Telegram session storage for bot access (pending)

- Persist Telegram Mini App JWTs in TelegramSession, expose a bot-key-protected endpoint for the bot to fetch/refresh tokens,
  and hydrate the bot FSM from backend sessions instead of sendData. See
  [DIFF 2025-12-19](./DIFF.codex.md#2025-12-19--codexfullstacktelegram-session-store-pending).
