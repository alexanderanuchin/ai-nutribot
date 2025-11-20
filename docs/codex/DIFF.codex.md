## 2025-12-26 – codex/infra/gateway-pid-fix (pending)

**Summary:** Keep the nginx reload sidecar in sync with the gateway’s PID namespace by giving the gateway a stable container nam
e and escape compose-time env substitution in the dev migration helper loop.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/docker-compose.yml | Pin the gateway container name so the nginx reload sidecar can join its PID namespace ins
tead of failing with “No such container: gateway”. | Infra | Recreate gateway/reloader |
| modify | infra/docker-compose.override.yml | Escape shell variables in the migration bootstrap loop to avoid compose-time env s
ubstitution warnings and keep per-app migration folders intact. | Backend dev env | Recreate backend |

## 2025-12-24 – codex/infra/letsencrypt-bootstrap (pending)

**Summary:** Stage 1 HTTPS readiness for caloiq.ru with webroot-based Let's Encrypt issuance/renewals (no gateway downtime), ACME served locally on port 80, background certbot + nginx reload sidecar, and an optional cron fallback.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/docker-compose.yml | Keep gateway on 80/8080, share `letsencrypt` and `certbot-webroot` volumes for webroot challenges, run continuous certbot renewals, and add an nginx reload sidecar without touching cloudpub. | Infra | Recreate Compose |
| create | infra/bootstrap-ssl.sh | Issue caloiq.ru certificates via webroot with gateway health checks and start the renewal/reloader sidecars post-issuance without stopping HTTP. | Infra ops | Recreate certbot/reloader |
| create | infra/renew-ssl.sh | Provide a manual webroot renew-and-reload helper plus optional cron snippet as a backup to the running certbot loop. | Infra ops | Reload gateway |
| modify | infra/nginx.conf | Serve ACME HTTP-01 locally and keep the gateway HTTP-only for stage 1 until certificates are issued. | Gateway | Reload nginx |

## 2025-12-23 – codex/bot/webhook-secret-raw (pending)

**Summary:** Preserve webhook secret tokens exactly as provided via environment variables so header verification is never skipped by URL validation.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/config.py | Keep WEBHOOK_SECRET untouched (or None when empty) instead of passing it through URL sanitization. | Bot runtime | Restart bot |

## 2025-12-22 – codex/bot/webhook-https-guard (pending)

**Summary:** Prevent Telegram webhook startup from crashing on non-HTTPS webhook URLs by validating the endpoint and falling back
to polling when Telegram rejects the webhook configuration.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/main.py | Validate webhook URL scheme, log HTTPS requirement breaches, and auto-switch to polling if Telegram rejects webhook setup. | Bot runtime | Restart bot |

## 2025-12-22 – codex/bot/webhook-env-sample (pending)

**Summary:** Documented the webhook configuration knobs in the shared env example so deployments can enable aiogram webhook mode
 consistently with configured URL, secret, port, and path.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/.env.example | Add WEBHOOK_* defaults (enable flag, HTTPS URL on caloiq.ru, secret, port, path) to guide webhook deployments. | Bot config | No |

## 2025-12-22 – codex/fullstack/telegram-webapp-confirm-flag (pending)

**Summary:** Align Telegram Mini App auth exchange with explicit confirmation flags, robust initData sourcing, reliable sendData delivery (including legacy field names and a short delivery cushion) before any optional close, and return JWTs to the WebApp so bot `sendData` payloads always contain tokens.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/auth/views.py | Collect initData from header/body/query safely and gate web_app auth confirmations behind explicit flags to keep the WebView open by default. | Backend auth | Restart backend |
| modify | backend/apps/users/tg_auth.py | Share confirmation flag helpers, make the legacy exchange endpoint opt-in for Mini App closure, normalize exp handling, and return access/refresh/exp in the exchange response so the WebApp can forward tokens to the bot. | Backend auth | Restart backend |
| modify | frontend/src/lib/telegram.ts | Harden initData discovery, defer WebView closing to explicit query flags, send auth payloads with legacy+current token keys, and pause briefly so sendData reaches the bot before navigation. | Frontend auth | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Record the Telegram confirmation flag alignment per Codex audit policy. | Docs | No |

## 2025-12-21 – codex/frontend/telegram-auth-runtime-stability (pending)

**Summary:** Kept the Mini App WebView open after initData exchange to avoid premature closure on desktop Telegram, and made the frontend tolerate backend auth responses that omit access/refresh tokens while still logging access presence.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Stop force-closing the WebView after initData exchange and treat tokens in the response as optional so SPA auth does not crash when backend suppresses JWTs. | Frontend auth | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Record the auth runtime stability adjustments per Codex audit policy. | Docs | No |

## 2025-12-11 – codex/bot/webapp-inline-auth (pending)

**Summary:** Switched the bot authorization CTA to an inline `web_app` button so Mini App launches always receive initData, mirroring the profile wizard’s markup, and let aiogram derive `allowed_updates` to ensure WebApp service payloads are delivered. Added coverage for HTTPS and non-HTTPS fallbacks and documented the change.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/keyboards/auth.py | Replace the reply keyboard auth CTA with an inline `web_app` button using the auth bridge URL. | Bot auth UX | Restart bot |
| modify | bot/tests/test_keyboards_auth.py | Assert inline keyboard rendering for HTTPS, fallback URL for non-HTTPS, and empty WebApp URL handling. | Bot tests | No |
| modify | bot/main.py | Allow aiogram to compute `allowed_updates` so `web_app_data` and other service messages are not filtered. | Bot runtime | Restart bot |
| modify | docs/codex/DIFF.codex.md | Record the inline auth keyboard swap per Codex audit policy. | Docs | No |

## 2025-12-10 – codex/bot/webapp-auth-bridge-buttons (pending)

**Summary:** Switched the bot’s auth CTAs to always launch the `/auth-bridge` Mini App via `web_app` buttons so Telegram clients pass initData, and covered the inline/reply keyboards with tests.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/keyboards/auth.py | Reuse a shared auth-bridge URL builder and keep reply keyboards opening the Mini App via web_app. | Bot auth UX | Restart bot |
| modify | bot/handlers/profile_wizard.py | Point the profile auth prompt to the `/auth-bridge` WebApp instead of a plain URL fallback. | Bot auth UX | Restart bot |
| modify | bot/tests/test_keyboards_auth.py | Cover the auth-bridge URL builder and reply keyboard bridge URL. | Bot tests | No |
| create | bot/tests/test_profile_wizard_auth.py | Assert the profile auth markup launches the WebApp bridge and falls back gracefully for non-HTTPS hosts. | Bot tests | No |
| modify | docs/codex/DIFF.codex.md | Record the WebApp auth CTA fix per Codex audit policy. | Docs | No |

## 2025-12-09 – codex/telegram-sse-hardening (pending)

**Summary:** Split Telegram CTA flows between Mini App SSO and classic login, gate chat SSE startup on confirmed linkage, throttle reconnection toasts, harden the auth bridge fallback, and serve the bridge stream with proper SSE headers across backend and nginx to eliminate 406 responses.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Add strict Mini App runtime detection (valid initData) and skip bot rehydrate outside Telegram. | Frontend auth | Rebuild frontend |
| modify | frontend/src/pages/AuthBridge.tsx | Redirect non-Mini App visitors to Telegram deeplinks instead of attempting browser auth. | Frontend auth | Rebuild frontend |
| modify | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Separate Mini App CTA to `/auth-bridge`, route the login CTA to `/login`, and pass linkage state to the chat shell diagnostics. | Frontend UI | Rebuild frontend |
| modify | frontend/src/components/integrations/TelegramChatShell.tsx | Defer EventSource startup until Telegram is linked, throttle reconnection toasts, and show a pre-linking hint. | Frontend UI | Rebuild frontend |
| modify | backend/apps/users/telegram_integration.py | Serve SSE with correct headers, return JSON 401/403 on auth errors, and bypass content negotiation 406 responses. | Backend API | Restart backend |
| modify | infra/nginx.conf | Configure SSE-friendly proxy settings for the Telegram bridge stream endpoint. | Infra proxy | Reload nginx |
| modify | docs/codex/DIFF.codex.md | Record the CTA split and SSE hardening per Codex audit policy. | Docs | No |

## 2025-11-16 – codex/frontend/telegram-integration (pending)

**Summary:** Delivered the Telegram integration surface at `/profile/integrations/telegram` with deep-link/QR helpers, chat
shell, and resilient backend endpoints for start payloads, status, and SSE bridge traffic. Added Telegram bot username setting
and persisted integration link codes for deep-link reuse.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/users/telegram_integration.py | Expose Telegram integration start/status endpoints, chat bridge send/stream, and query-param JWT auth for SSE. | Backend API | Restart backend |
| modify | backend/apps/users/urls.py | Wire the Telegram integration routes under `/api/users/`. | Backend API | Restart backend |
| modify | backend/apps/users/models.py | Persist integration deep-link payloads with expiry/status tracking. | Backend data | Migrations |
| create | backend/apps/users/migrations/0011_telegramintegrationlink.py | Create the TelegramIntegrationLink model and supporting indexes. | Backend data | Apply migration |
| modify | backend/nutribot/settings.py | Configure a TELEGRAM_BOT_USERNAME env setting for deep-link builders. | Backend config | Restart backend |
| create | frontend/src/lib/deeplinks.ts | Provide reusable Telegram start/startapp link builders. | Frontend utilities | Rebuild frontend |
| create | frontend/src/lib/qr.ts | Generate QR codes for deep-link sharing via the UI. | Frontend utilities | Rebuild frontend |
| modify | frontend/src/lib/telegram.ts | Detect WebApp presence and open Telegram links via SDK or browser fallback. | Frontend utilities | Rebuild frontend |
| create | frontend/src/api/telegram.ts | Add client helpers for integration status, link start, and bridge send. | Frontend API | Rebuild frontend |
| create | frontend/src/components/integrations/TelegramHeroCard.tsx | Hero block with CTA buttons and QR for the integration page. | Frontend UI | Rebuild frontend |
| create | frontend/src/components/integrations/TelegramHowItWorks.tsx | Explain the 3-step Mini App handshake flow. | Frontend UI | Rebuild frontend |
| create | frontend/src/components/integrations/TelegramStatusCard.tsx | Show link status, deep-links, QR, and diagnostics. | Frontend UI | Rebuild frontend |
| create | frontend/src/components/integrations/TelegramChatShell.tsx | Implement the SSE-backed chat shell with optimistic sends. | Frontend UI | Rebuild frontend |
| create | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Assemble the integration screen with hero, steps, status, and chat. | Frontend page | Rebuild frontend |
| modify | frontend/src/App.tsx | Register the Telegram integration route while keeping the auth bridge accessible. | Frontend routing | Rebuild frontend |
| modify | frontend/package.json | Add qrcode dependency for QR generation. | Frontend tooling | Reinstall deps |
| modify | frontend/package-lock.json | Lock dependency tree after adding qrcode. | Frontend tooling | Reinstall deps |

## 2025-12-07 – codex/webapp-auth-bridge (pending)

**Summary:** Implemented the Telegram Mini App auth bridge with a reply-keyboard
CTA, `/auth-bridge` route that sends `sendData` immediately and closes, guarded
auto-rehydrate + MainButton fallback, richer telemetry (env/auth/sendData), and
bot-side `web_app_data` logging/confirmation so JWT delivery is observable and
resilient. Follow-up refinements tightened `sendData` payloads/telemetry and
import hygiene.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | bot/keyboards/auth.py | Provide the reply-keyboard WebApp bridge button that opens `/auth-bridge` with `web_app` info. | Bot UX | Restart bot |
| modify | bot/handlers/wallet.py | Use the bridge keyboard for unauthorized wallet flows to force reliable sendData delivery. | Bot UX | Restart bot |
| modify | bot/handlers/profile_wizard.py | Reuse the bridge keyboard when WebApp top-ups need fresh auth. | Bot UX | Restart bot |
| modify | bot/handlers/webapp_data.py | Log received `web_app_data` keys, harden JSON parsing, and confirm auth to the user. | Bot telemetry | Restart bot |
| create | bot/tests/test_keyboards_auth.py | Cover the auth bridge keyboard URL shaping and empty-url fallback. | Bot tests | No |
| modify | bot/tests/test_wallet_handlers.py | Align wallet auth prompt expectations with the reply-keyboard bridge. | Bot tests | No |
| create | frontend/src/pages/AuthBridge.tsx | Add the forced-auth webview that bootstraps auth, sends the `auth` payload, and closes. | Frontend WebApp | Rebuild frontend |
| modify | frontend/src/App.tsx | Route `/auth-bridge` even before auth so bot CTA can complete the handshake. | Frontend routing | Rebuild frontend |
| modify | frontend/src/lib/telegram.ts | Guard rehydrate sendData to a single attempt, add MainButton fallback, and log init-data gaps. | Frontend auth/telemetry | Rebuild frontend |
| modify | frontend/src/main.tsx | Bootstrap Telegram auth before rendering to unblock early sendData. | Frontend startup | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Note the Mini App auth bridge milestone. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this bridge implementation per audit policy. | Docs | No |
| modify | frontend/src/pages/AuthBridge.tsx | Ensure auth bridge always emits compact auth payload with exp/exp_at, logs sendData success/fail, and closes WebApp. | Frontend WebApp | Rebuild frontend |
| modify | frontend/src/lib/telegram.ts | Add telemetry extras for environment/auth/sendData and include WebApp capability flags. | Frontend auth/telemetry | Rebuild frontend |
| modify | frontend/src/api/telegram.ts | Fix API client import to use the default export. | Frontend API | Rebuild frontend |
| modify | frontend/src/components/integrations/TelegramChatShell.tsx | Use the correct API client import in the chat shell. | Frontend UI | Rebuild frontend |

## 2025-12-06 – codex/infra/retire-cloudpub-stack (pending)

**Summary:** Retired the CloudPub publication setup and scrubbed its
hostname from configuration defaults so only the caloiq.ru domain family
is referenced across services and tooling.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/docker-compose.yml | Drop the CloudPub agent service and volume now that deployments run directly on caloiq.ru. | Infra local | Recreate Compose |
| modify | infra/.env.example | Remove CloudPub host defaults and tokens so sample envs align with the active domain. | Infra config | No |
| modify | frontend/vite.config.ts | Limit dev proxy host allowances to caloiq.ru variants after CloudPub retirement. | Frontend tooling | No |
| modify | backend/nutribot/settings.py | Trim CSRF trusted origins to the caloiq.ru hosts so backend security config matches production. | Backend config | Restart backend |
| modify | backend/tests/test_settings.py | Refresh host parsing tests to cover only caloiq.ru and generic sample domains. | Backend tests | No |
| modify | docs/codex/DIFF.codex.md | Record the CloudPub removal per Codex audit policy. | Docs | No |

## 2025-12-05 – codex/bot/wallet-webapp-url (pending)

**Summary:** Ensure every wallet entry point receives the configured WebApp URL
so authorization prompts render the correct button instead of crashing on
missing handler arguments when navigating from the main menu or quick actions.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/routers/menu.py | Thread the WebApp URL into wallet handlers invoked from menu actions and quick actions to keep authorization prompts consistent. | Bot UX | Restart bot |
| modify | docs/codex/DIFF.codex.md | Record the wallet handler wiring fix per Codex audit policy. | Docs | No |

## 2025-12-04 – codex/bot/stars-idempotency (pending)

**Summary:** Anchor the plan hold idempotency base to the Telegram user and attempt
identifier so duplicate callbacks or retries reuse the same hold key lineage.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/handlers/plan.py | Derive Stars hold idempotency bases from `telegram_user_id` + `attempt_id` to keep retries idempotent across hold/consume/release. | Bot UX | Restart bot |
| modify | docs/codex/DIFF.codex.md | Record the deterministic idempotency base adjustment per Codex policy. | Docs | No |

## 2025-12-04 – codex/bot/stars-monetization-stage3-end (pending)

**Summary:** Polished the Stage 3 Telegram bot monetization flow by rebuilding the
plan handler with attempt-tracked holds, consistent Stars block messaging, and
symmetrical audit logs that feed automatic resumes. Shared the blocked-text
constant across handlers, ensured invoice logging carries action metadata, and
expanded tests to cover new UX copy, job release paths, and backend hold
context.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/constants.py | Provide a single Stars blocked message string for reuse across plan, wallet, and profile flows. | Bot UX | Restart bot |
| modify | bot/payments/stars.py | Ensure Stars invoice logging records the action metadata alongside provider tokens. | Bot telemetry | Restart bot |
| modify | bot/handlers/plan.py | Rebuild plan generation with attempt-aware hold lifecycle logging, updated UX copy, and auto-resume safeguards. | Bot UX | Restart bot |
| modify | bot/handlers/profile_wizard.py | Reuse the shared Stars block copy and enrich telemetry for WebApp-triggered resumes. | Bot UX | Restart bot |
| modify | bot/handlers/wallet.py | Align wallet flows with the shared block message and attempt/action logging before resuming plan generation. | Bot UX | Restart bot |
| modify | bot/handlers/webapp_data.py | Pass through attempt/action metadata and Stars block UX for WebApp top-ups. | Bot WebApp UX | Restart bot |
| modify | bot/tests/test_plan_handler.py | Cover the new insufficient/receipt copy, attempt-id handoff, and job failure/time-out releases. | Bot tests | No |
| modify | bot/tests/test_wallet_handlers.py | Expect the shared Stars block message and keep wallet resume telemetry in sync. | Bot tests | No |
| modify | backend/apps/orders/tests/test_wallet_and_orders.py | Assert wallet hold APIs merge pricing context metadata for plan periods. | Backend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Log the Stage 3 Stars monetization completion per Codex policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit record. | Docs | No |

## 2025-12-04 – codex/bot/stars-monetization (pending)

**Summary:** Finished Stage 3 bot monetization: backend exposes wallet pricing/hold
APIs, threads the Telegram provider token through all invoices, annotates
payments with plan intents/attempts for safe auto-resume, persists Stars block
state in the FSM, and tests cover pricing, holds, payment metadata, and plan
generation end to end. Added plan-specific top-up UX with deterministic
idempotency keys, shared Stars invoice helpers, hold context forwarding, and
documentation/env defaults for server-side pricing.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/orders/services/pricing.py | Centralise wallet action pricing resolution so views can reuse defaults and validation. | Backend API | Restart backend |
| modify | backend/apps/orders/views.py | Add `/wallet/pricing/` and hold lifecycle endpoints, surface Stars block flags, accept contextual pricing payloads, and log deterministic hold/consume/release keys. | Backend API | Restart backend |
| modify | backend/apps/orders/services/telegram_invoice.py | Pass the configured provider token through Bot API invoice links. | Backend payments | Restart backend |
| modify | backend/apps/orders/urls.py | Expose the pricing and hold endpoints under the existing orders namespace. | Backend API | Restart backend |
| modify | backend/apps/orders/tests/test_wallet_and_orders.py | Cover pricing defaults, Stars block flags, hold idempotency, and contextual plan-period requests. | Backend tests | No |
| modify | backend/nutribot/settings.py | Provide default wallet action pricing and thread the Telegram provider token env fallback. | Backend config | Restart backend |
| modify | infra/.env.example | Document TELEGRAM provider fallback and expose Stars pricing defaults for plan generation. | Infra config | No |
| modify | bot/backend_client.py | Teach the client pricing/hold/report helpers, pass idempotency keys, and forward hold context for plan periods. | Bot↔ backend API | Restart bot |
| modify | bot/config.py | Load the Telegram Stars provider token from env for invoice issuance. | Bot configuration | Restart bot |
| modify | bot/middlewares/store.py | Inject the provider token into handler context for invoice builders. | Bot runtime | Restart bot |
| modify | bot/keyboards/plan.py | Add the plan-specific Stars top-up keyboard with preset amounts and WebApp/support fallbacks. | Bot UX | Restart bot |
| create | bot/payments/__init__.py | Export shared Stars invoice builders for bot handlers. | Bot runtime | Restart bot |
| create | bot/payments/stars.py | Centralise Stars invoice payload building/parsing and plan intent metadata. | Bot runtime | Restart bot |
| modify | bot/handlers/plan.py | Orchestrate holds with deterministic idempotency, plan-specific top-ups, contextual pricing, and automatic release/resume logging. | Bot UX | Restart bot |
| modify | bot/handlers/wallet.py | Consume shared invoice helpers, respect plan metadata, and continue attempt-checked resumes post top-up. | Bot UX | Restart bot |
| modify | bot/handlers/profile_wizard.py | Reuse the shared invoice builder with provider token/plan metadata and block-region fallbacks. | Bot UX | Restart bot |
| modify | bot/handlers/webapp_data.py | Ensure WebApp-issued invoices include provider token, plan metadata, and respect Stars blocks. | Bot WebApp UX | Restart bot |
| create | bot/constants.py | Share quick top-up presets without circular imports between handlers. | Bot runtime | Restart bot |
| modify | bot/tests/test_wallet_handlers.py | Extend coverage for payment logging, attempt metadata, and plan resume hooks. | Bot tests | No |
| modify | bot/tests/test_webapp_data.py | Add coverage for plan-linked invoice payloads and Stars block fallbacks. | Bot tests | No |
| modify | bot/tests/test_plan_handler.py | Exercise holds, insufficient balance prompts, attempt ids, payment resumes, and plan-specific top-up invoices. | Bot tests | No |
| create | bot/tests/conftest.py | Silence audit log handlers and allow async-unsafe DB ops inside async bot tests. | Bot tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Capture the Telegram Payments wiring (provider token, invoice metadata, retries) in the changelog. | Docs | No |
| modify | backend/README.md | Document the Stars pricing env variables powering wallet holds. | Docs | No |

## 2025-12-03 – codex/bot/stage2-launcher (pending)

**Summary:** Delivered the Stage 2 launcher experience: hero start card with
compact inline actions, a consolidated Info & Legal surface, wallet login
prompts tuned for the modern flow, and bot-wide command/menu polish including
the Chat Menu WebApp shortcut.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/config.py | Read the hero image URL from env so `/start` can send the brand cover. | Bot UX | Restart bot |
| modify | bot/middlewares/store.py | Expose the hero image to handlers via middleware context. | Bot runtime | No |
| modify | bot/utils/texts.py | Refresh start copy with the Stage 2 pitch and CTA. | Bot UX | No |
| modify | bot/keyboards/main_menu.py | Rebuild the inline menu into a 2×2 grid with Info & Legal action. | Bot UX | No |
| modify | bot/handlers/support.py | Add Info & Legal renderer with inline links and contact CTA. | Bot UX | No |
| modify | bot/routers/menu.py | Wire the new Info & Legal action, menu callback, and fallbacks. | Bot UX | No |
| modify | bot/routers/commands.py | Send the hero image card on `/start` with the updated keyboard. | Bot UX | No |
| modify | bot/handlers/wallet.py | Introduce the “Нужно войти” prompt and reuse it across wallet flows. | Bot UX | No |
| modify | bot/services/commands.py | Trim command menu per spec and configure the Chat Menu WebApp button. | Bot UX | Bot restart |
| modify | bot/main.py | Invoke chat menu setup during startup. | Bot runtime | Restart bot |
| modify | bot/tests/test_wallet_handlers.py | Align tests with the new wallet login messaging. | Bot tests | No |

## 2025-12-02 – codex/bot/stage1-bootstrap (pending)

**Summary:** Delivered Stage 1 of the Telegram bot overhaul: introduced a
standard `bot.main` entrypoint with signal-aware polling, centralised logging
via `logkit`, simplified the `/start` UX into the minimal inline launcher, and
threaded legal/support links through the configuration and handlers.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | bot/logkit.py | New logging toolkit with context-based `rid`, JSON/text formatters, and a lightweight `TelemetryLogger` per Stage 1 logging requirements. | Bot runtime | No |
| create | bot/main.py | Standard async entrypoint (`python -m bot.main`) with graceful SIGINT/SIGTERM shutdown and central dispatcher wiring. | Bot runtime | Restart bot |
| modify | bot/app.py | Delegate legacy script entrypoint to the new `bot.main` runner. | Bot runtime | No |
| modify | bot/backend_client.py | Align backend telemetry with `logkit` (`rid` extras only) and reuse the new request-id helpers. | Bot ↔ backend telemetry | No |
| modify | bot/config.py | Consolidate env parsing (redis, legal URLs, experimental flag) and expose HTTPS-aware WebApp helpers. | Bot configuration | Bot restart |
| modify | bot/handlers/support.py | Generate support/terms texts from env-sourced URLs for inline menu usage. | Bot UX | No |
| modify | bot/handlers/wallet.py | Switch to `logkit` rid handling for wallet telemetry. | Bot telemetry | No |
| modify | bot/handlers/webapp_data.py | Use new logging helpers and strip legacy `request_id` fields from WebApp auth/top-up flows. | Bot telemetry | No |
| modify | bot/healthcheck.py | Track renamed backend URL constants from the unified config. | Bot tooling | No |
| modify | bot/keyboards/main_menu.py | Rebuild main menu as an inline launcher with WebApp/browser buttons plus compact action row. | Bot UX | No |
| delete | bot/logging_utils.py | Retire legacy logging helpers in favour of `bot/logkit.py`. | Bot runtime | No |
| modify | bot/middlewares/logging.py | Emit telemetry through `TelemetryLogger` and honour context-provided `rid`. | Bot telemetry | No |
| modify | bot/middlewares/store.py | Inject the full `Config` object and expose legal/support URLs & experiment flag to handlers. | Bot dependency wiring | No |
| modify | bot/middlewares/throttle.py | Read request ids via `logkit` to keep throttling logs consistent. | Bot telemetry | No |
| modify | bot/routers/commands.py | Produce the minimalist `/start` screen, reuse `Config`, and gate quick actions behind `BOT_EXPERIMENTAL_MENU`. | Bot UX | No |
| modify | bot/routers/errors.py | Switch to new logging helpers and drop the outdated reply keyboard on error fallback. | Bot UX | No |
| modify | bot/routers/menu.py | Handle new inline menu callbacks while keeping legacy text fallbacks and threading config-derived URLs. | Bot UX | No |
| modify | bot/utils/texts.py | Provide concise start/cancel copy tailored to the Stage 1 launcher. | Bot UX | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the Stage 1 bot bootstrap milestone per Codex policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit log entry. | Docs | No |

## 2025-12-01 – codex/backend/admin-static-assets (pending)

**Summary:** Serve admin static assets via WhiteNoise, collect them during
container startup, and pin the dependency so Jazzmin and Django admin regain
their styles/scripts behind Gunicorn.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/nutribot/settings.py | Insert WhiteNoise middleware and compressed manifest storage so Gunicorn can serve collected admin/static assets. | Backend runtime | Restart backend |
| modify | backend/entrypoint.sh | Run `collectstatic` on startup (with opt-out) to populate WhiteNoise's manifest in containers. | Backend runtime | Restart backend |
| modify | backend/requirements.txt | Declare the WhiteNoise dependency for static asset serving. | Backend deps | Rebuild backend image |
| modify | backend/requirements.lock | Regenerate lockfile to include WhiteNoise and keep hashes in sync. | Backend deps | Rebuild backend image |
| modify | docs/codex/CHANGELOG.codex.md | Record the admin static asset hardening per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit entry for admin static asset recovery. | Docs | No |

## 2025-11-30 – codex/infra/feed-ws-asgi (pending)

**Summary:** Run the Docker Compose backend through Uvicorn so feed WebSocket
handshakes reach Channels during development and stretch the `/ws/` proxy
timeouts to avoid idle disconnects when CloudPub holds open upgrades.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/docker-compose.override.yml | Switch `runserver` to `uvicorn nutribot.asgi:application --reload` so local stacks exercise the ASGI app instead of Django's WSGI dev server. | Backend dev infra | Restart backend |
| modify | backend/README.md | Document the Uvicorn dev startup so manual checks follow the ASGI path required for `/ws/feed` upgrades. | Docs | No |
| modify | infra/nginx.conf | Extend `/ws/` proxy timeouts to `1d` to keep idle feed WebSocket sessions connected behind CloudPub. | Infra realtime | Reload Nginx |

## 2025-11-29 – codex/frontend/feed-realtime-handshake (pending)

**Summary:** Degrade feed WebSocket handshake retries after the first refused
upgrade so the console no longer logs three consecutive failures on every tab
switch while keeping post-handshake reconnects and SSE fallback behaviour
covered by tests.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.ts | Short-circuit WebSocket retries when the socket never opens, track open-close streaks separately from exponential backoff, and reset streaks on SSE fallback so navigation logs just one failure before switching transport. | Frontend realtime | No |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.test.tsx | Refresh realtime tests to assert immediate SSE fallback on handshake failures while preserving reconnect attempts after established sockets close. | Frontend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the feed realtime handshake fallback refinement per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit entry for realtime handshake fallback coverage. | Docs | No |

## 2025-11-28 – codex/infra/multi-domain (pending)

**Summary:** Accept CloudPub and Caloiq published domains end-to-end so backend CSRF checks,
CORS, and the frontend dev proxy recognise both without manual overrides.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/nutribot/settings.py | Trust Caloiq wildcard hosts for CSRF alongside CloudPub defaults so published sessions survive domain switchover. | Backend security | Restart backend |
| modify | backend/tests/test_settings.py | Extend host parsing coverage to include Caloiq domains and confirm helper merges remain deterministic. | Backend tests | No |
| modify | infra/.env.example | Document Caloiq in default CORS origins so deployments enable the new domain without manual tweaks. | Infra config | Restart backend |
| modify | frontend/vite.config.ts | Allow Caloiq hostnames through the dev proxy (including `caloiq.ru`) and normalise the published host parsing for HMR so local previews work for both published domains. | Frontend tooling | No |
| modify | docs/codex/CHANGELOG.codex.md | Log the dual-domain enablement per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit trail entry for traceability. | Docs | No |

## 2025-11-27 – codex/frontend/feed-manual-refresh (pending)

**Summary:** Keep the manual refresh CTA responsive even while realtime-driven refetches are running and avoid state updates after unmount.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/Feed.tsx | Track manual refresh progress locally and guard async cleanup so background refetches no longer disable the button. | Frontend UX | No |

## 2025-11-26 – codex/backend/feed-ws-allowed-hosts (pending)

**Summary:** Auto-extend `ALLOWED_HOSTS` with frontend origins so feed WebSocket
handshakes succeed on CloudPub without exhausting the retry budget before
falling back to SSE.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/nutribot/settings.py | Include hosts parsed from `DJANGO_CORS_ORIGINS`/`WEBAPP_URL` so Channels accepts CloudPub websocket origins without changing `_parse_allowed_hosts`'s contract. | Backend realtime | Restart backend |
| modify | backend/tests/test_settings.py | Cover allowed-host parsing helpers and the `_extend_allowed_hosts` layer to ensure environment-provided origins surface in runtime defaults. | Backend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Capture the allowed-host enrichment per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append audit entry for allowed-host enrichment. | Docs | No |

## 2025-11-25 – codex/backend/feed-ws-origin (pending)

**Summary:** Allow intermediate proxies to forward `/ws/feed` with or without a leading slash
and prove authenticated upgrades succeed via Channels without depending on Daphne.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/feed/routing.py | Accept an optional leading slash so CloudPub-originated WebSocket requests reach the feed consumer instead of Django's 404 handler. | Backend realtime | No |
| modify | backend/tests/test_feed_websocket.py | Stub Daphne, spin up a ProtocolTypeRouter, and assert authenticated handshakes succeed with `/ws/feed` so regression surfaces in CI. | Backend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the proxy-tolerant routing and handshake test per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit trail entry. | Docs | No |

## 2025-11-24 – codex/backend/feed-ws-routing (pending)

**Summary:** Allow feed WebSocket connections to resolve with or without a trailing
slash and cover the ASGI handshake with channel tests so `/ws/feed` no longer
falls back to Django's 404 handler before SSE recovery.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/feed/routing.py | Accept optional trailing slashes on the feed WebSocket route so `/ws/feed` hits Channels instead of the HTTP 404 view. | Backend realtime | No |
| create | backend/tests/test_feed_websocket.py | Assert authenticated connections succeed for `/ws/feed/` and `/ws/feed` to guard against regression. | Backend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the feed WebSocket routing fix in the changelog. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append audit entry for the feed WebSocket routing fix. | Docs | No |

## 2025-11-24 – codex/frontend/feed-realtime-bases (pending)

**Summary:** Align feed realtime base resolver expectations with the `/ws/` proxy,
extend coverage so SSR and browser paths stay in sync, and assert the feed hook
produces host-level WebSocket URLs.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | frontend/src/utils/realtime.test.ts | Cover HTTP/WS base resolution paths and update expectations away from the legacy `/api` suffix. | Frontend tests | No |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.test.tsx | Ensure the feed realtime hook dials `ws(s)://<host>/ws/...` with new resolver defaults. | Frontend realtime tests | No |
| modify | frontend/src/utils/realtime.ts | Normalise file termination while validating resolver behaviour under the new proxy. | Frontend realtime | No |
| modify | docs/codex/CHANGELOG.codex.md | Record realtime base resolver coverage per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append audit entry for realtime base resolver adjustments. | Docs | No |

## 2025-11-24 – codex/infra/feed-ws-proxy (pending)

**Summary:** Route feed WebSocket traffic through Nginx so realtime clients can upgrade connections in production, and disable proxy buffering for SSE fallbacks to prevent protocol errors.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/nginx.conf | Proxy /ws/ requests to Django Channels with WebSocket headers and add unbuffered SSE passthrough for `/api/v1/*/events` so realtime clients stay connected. | Infra realtime | Reload Nginx |
| modify | docs/codex/DIFF.codex.md | Record the WebSocket and SSE proxy hardening for audit traceability. | Docs | No |

## 2025-11-12 – codex/backend/market-sse-byte-adapter (pending)

**Summary:** Normalize marketplace SSE payload chunks so formatter outputs always reach clients as
valid bytes, even when third-party hooks yield bare `bytes` or malformed iterables.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/api/events.py | Wrap feed formatter output so SSE streams always emit bytes and fall back to manual framing on formatter errors. | Backend realtime API | No |
| modify | backend/apps/market/tests/test_events_api.py | Reproduce byte-returning and malformed chunk formatters to assert SSE responses stay valid bytes. | Backend tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Log the SSE formatter adapter per Codex changelog requirements. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record the SSE formatter adapter entry for audit traceability. | Docs | No |

## 2025-11-23 – codex/frontend/feed-realtime-ws-cleanup (pending)

**Summary:** Defers closing CONNECTING feed WebSockets to eliminate Chrome's "connection closed"
noise during fast tab switches while keeping SSE fallbacks healthy and covered by richer tests.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.ts | Defer closing CONNECTING sockets until their `open` event before closing to avoid browser noise without regressing reconnect logic. | Frontend realtime | No |
| modify | frontend/src/features/feed/hooks/useFeedRealtime.test.tsx | Strengthen mocks and async sequencing to verify deferred closes and SSE fallback delivery. | Frontend tests | No |
| modify | docs/codex/DIFF.codex.md | Capture the feed realtime cleanup per Codex audit policy. | Docs | No |

## 2025-11-22 – codex/frontend/radix-aschild-compat (pending)

**Summary:** Filtered Radix `asChild` control props out of shared UI kit primitives so they no longer leak onto DOM nodes and tr
## 2025-11-15 – codex/frontend/remove-legacy-cloudpub-domain (pending)

**Summary:** Retired the obsolete CloudPub vanity host from the frontend defaults and
backend config tests so the stack now only references the caloiq.ru domain family.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/vite.config.ts | Point the default published host at caloiq.ru so dev HMR follows the production domain. | Frontend dev server | No |
| modify | backend/tests/test_settings.py | Refresh allowed host extension tests to expect caloiq.ru after removing the CloudPub hostname. | Backend tests | No |
| modify | docs/codex/DIFF.codex.md | Log the domain cleanup per Codex audit requirements. | Docs | No |

## 2025-11-12 – codex/backend/market-sse-renderer (pending)

**Summary:** Restored marketplace SSE compatibility with DRF by adding an event-stream renderer,
request-scoped logging, strict resource validation, and dropping hop-by-hop headers so EventSource
clients receive proper responses instead of 406/500 errors.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/api/events.py | Attach an SSE renderer, authenticate failures via DRF exceptions, stream broker events with request-id logging, and omit hop-by-hop headers to satisfy EventSource negotiation. | Backend API | No |
| modify | backend/apps/market/tests/test_events_api.py | Ensure SSE response tests reflect dropped `Connection` header so the regression stays covered. | Backend tests | No |
| modify | docs/codex/DIFF.codex.md | Record SSE renderer compatibility fix per Codex audit policy. | Docs | No |

igger React warnings.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/ui/Button.tsx | Discard the `asChild` slot prop before forwarding DOM attributes to animated buttons/links to stop unsupported attribute warnings. | Frontend UI kit | No |
| modify | frontend/src/components/ui/IconButton.tsx | Ignore Radix `asChild` when composing icon buttons so close triggers and overlays remain warning-free. | Frontend UI kit | No |
| modify | frontend/src/components/ui/Card.tsx | Drop `asChild` from card props to prevent sheet/dialog contents rendered via Radix slots from leaking the flag into the DOM. | Frontend UI kit | No |
| modify | docs/codex/DIFF.codex.md | Record Radix slot compatibility refinement per Codex audit requirements. | Docs | No |

## 2025-11-21 – codex/frontend/realtime-index-guards (pending)

**Summary:** Hardened command palette and market search selection effects to clamp their
highlighted indices with functional updates, preventing runaway re-renders when result
lists shrink rapidly.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/nav/CommandPanel.tsx | Clamp the active command entry index via functional state updates so shrinking result sets cannot trigger repeated `setState` loops. | Frontend UX | No |
| modify | frontend/src/features/market/components/MarketSearch.tsx | Normalise market search result index resets using range-safe updates to avoid redundant renders during rapid data refreshes. | Frontend UX | No |
| modify | docs/codex/DIFF.codex.md | Record realtime selection guard refinements per Codex audit policy. | Docs | No |

## 2025-11-20 – codex/frontend/market-cart-integration (pending)

**Summary:** Unified marketplace checkout state, restored the cart summary on the meal plan programs page, and lifted the mobile cart bar above the tab bar for consistent purchasing across sections.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | frontend/src/features/market/hooks/useMarketCheckout.ts | Centralise cart totals, wallet logic, and checkout mutations for reuse across marketplace pages. | Frontend UX | No |
| create | frontend/src/features/market/components/MarketSummary.tsx | Share desktop/mobile cart & plan summary UI between catalogue screens. | Frontend UX | No |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Consume the shared checkout hook and summary components to simplify state and keep behaviour consistent. | Frontend UX | No |
| modify | frontend/src/pages/market/MarketMealPlansPage.tsx | Add cart summary controls, refocusable search, and responsive layout so programs support end-to-end purchase flows. | Frontend UX | No |
| modify | frontend/src/features/market/constants.ts | Refresh the programs navigation description to highlight expert-curated plans. | Frontend UX | No |
| modify | frontend/src/components/nav/MobileTabBar.tsx | Measure and expose tab bar height so floating cart bars clear the mobile navigation. | Frontend UX | No |
| modify | docs/codex/DIFF.codex.md | Log cart integration updates per Codex audit policy. | Docs | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the marketplace cart integration milestone. | Docs | No |

## 2025-11-19 – codex/frontend/navdrawer-theming (pending)

**Summary:** Normalised light-theme colours for the mobile navigation drawer so inactive buttons keep the intended neutral text tone while hovering and focusing.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/nav/NavDrawer.tsx | Force neutral text colours for inactive drawer links to avoid primary-colour bleed on light theme hovers. | Frontend UX | No |
| modify | docs/codex/DIFF.codex.md | Log navigation drawer colour fix per Codex audit policy. | Docs | No |

## 2025-11-18 – codex/infra/mypy-bootstrap (pending)

**Summary:** Enabled mypy with Django-aware stubs, tightened typing around logging/ETL utilities,
and added a reproducible `make typecheck` target for backend contributors.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/requirements.txt | Add mypy and Django/DRF stub packages for local installs. | Backend tooling | Reinstall backend deps |
| modify | backend/requirements.lock | Regenerate lock file with type-checking dependencies. | Backend tooling | Reinstall backend deps |
| modify | mypy.ini | Configure Django plugin, strict optional checks, and tuned follow-imports. | Backend typing | No |
| modify | backend/nutribot/settings.py | Type-safe feed source loader for mypy coverage. | Backend config | No |
| modify | backend/apps/feed/adapters/rss.py | Ensure helper returns canonical strings. | Backend services | No |
| modify | backend/apps/catalog/etl/usda.py | Harden numeric parsing and summary typing for ETL. | Backend services | No |
| modify | backend/nutribot/middleware.py | Annotate request logging middleware and formatters. | Backend infra | No |
| modify | backend/nutribot/asgi.py | Guard channel layer lookup for type checking. | Backend infra | No |
| modify | backend/apps/common/renderers.py | Align renderer override signature with DRF stubs. | Backend API | No |
| modify | backend/apps/feed/events.py | Introduce typed feed event broker and payload protocol. | Backend services | No |
| create | Makefile | Provide `make typecheck` helper wrapping mypy env wiring. | Developer ergonomics | No |
| modify | backend/README.md | Document the new type checking workflow. | Docs | No |
| modify | docs/codex/CHANGELOG.codex.md | Record typing bootstrap milestone. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append traceability entry for mypy integration. | Docs | No |

## 2025-11-18 – codex/fullstack/telegram-webapp-flow (pending)

**Summary:** Stopped auto-closing the Telegram Mini App from the backend, added opt-in confirmation toggles, broadened initData collection to include query/hash payloads, and restored `sendData` delivery of auth tokens before any optional WebView close.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/auth/views.py | Accept initData from header/body/query sources and only answer WebApp queries when explicitly requested. | Backend auth | Restart backend |
| modify | backend/apps/users/tg_auth.py | Reuse boolean coercion for query flags and gate Telegram auth confirmations on an opt-in flag. | Backend/bot auth handshake | Restart backend |
| modify | frontend/src/lib/telegram.ts | Read initData from runtime/hash/query, send auth tokens to the bot via `sendData` before optionally closing the WebView, and keep redirects stable. | Frontend auth | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Log the Telegram WebApp flow hardening per Codex policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit entry. | Docs | No |

## 2025-11-17 – codex/infra/lint-style (pending)

**Summary:** Unified Python and frontend lint/format configurations by introducing Ruff-wide
exclusions and React-aware ESLint/Prettier setup to standardise code style enforcement across the
monorepo.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | ruff.toml | Extend Ruff to cover backend/bot modules with shared exclusions and
formatting defaults. | Python linting | No |
| modify | frontend/eslint.config.mjs | Adopt flat ESLint config with React/hook plugins and
shared env defaults. | Frontend linting | No |
| create | frontend/prettier.config.mjs | Provide Prettier formatting baseline aligned with project
print width and quoting style. | Frontend formatting | No |
| modify | frontend/package.json | Wire unified lint/format scripts and add globals dependency for
lint config. | Frontend tooling | npm install |
| modify | frontend/package-lock.json | Lock updated dev dependency graph after lint tooling
changes. | Frontend tooling | npm install |
| modify | docs/codex/CHANGELOG.codex.md | Record lint/style consolidation milestone per Codex
changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append traceability entry for lint/style standardisation. |
Docs | No |

## 2025-11-16 – codex/infra/ci-workflow (pending)

**Summary:** Introduced GitHub Actions CI pipeline with cached security audits and frontend/backend quality checks on Python 3.12 and Node 22 runners.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | .github/workflows/ci.yml | Provide converged CI pipeline with concurrency-safe audits and quality checks for monorepo services. | Infra CI | No |
| modify | docs/codex/CHANGELOG.codex.md | Register CI workflow milestone per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append traceability record for CI workflow introduction. | Docs | No |

## 2025-11-09 – codex/security/dependency-refresh (pending)

**Summary:** Regenerated backend/bot lock files and upgraded the frontend build toolchain (Vite 6.4 + Vitest 4) to clear pip/npm audit findings while enforcing Node 20.19+ runtime support.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/requirements.txt | Raise `djangorestframework-simplejwt` to the patched 5.5 series for JWT security fixes. | Backend deps | Yes (rebuild backend image) |
| create | backend/requirements.lock | Capture deterministic backend dependency graph via `pip-compile`. | Backend deps | Yes (rebuild backend image) |
| modify | bot/requirements.txt | Bump `aiohttp` to 3.12 for upstream CVE remediation. | Bot deps | Yes (rebuild bot image) |
| create | bot/requirements.lock | Lock bot dependencies for reproducible deploys. | Bot deps | Yes (rebuild bot image) |
| modify | frontend/package.json | Enforce Node 20.19+/22 engines and upgrade Vite/vitest/react tooling to vulnerability-free releases. | Frontend build | npm install |
| modify | frontend/package-lock.json | Refresh lock graph after dependency upgrades. | Frontend build | npm install |
| modify | docs/codex/CHANGELOG.codex.md | Log dependency refresh milestone per Codex changelog policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record dependency security refresh artefacts for traceability. | Docs | No |

## 2025-11-15 – codex/infra/container-hardening (pending)

**Summary:** Hardened runtime containers for backend, bot, and frontend services with multi-stage builds, non-root execution, explicit health probes, and compose alignment for venv usage.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/Dockerfile | Adopt multi-stage build with isolated venv, non-root user, dedicated runtime dir, and resilient health probe fallback between `/healthz` and `/metrics`. | Backend infra | Yes (rebuild backend image) |
| modify | backend/entrypoint.sh | Ensure POSIX sh compatibility, prefer `/opt/venv/bin`, and invoke manage.py commands via absolute interpreter. | Backend runtime | Yes (rebuild backend image) |
| modify | bot/Dockerfile | Introduce multi-stage build, copy venv, drop root privileges, and wire Python healthcheck module. | Bot infra | Yes (rebuild bot image) |
| modify | bot/config.py | Prefer `BACKEND_API_URL` while keeping legacy aliases for backward compatibility. | Bot config | Bot restart |
| create | bot/healthcheck.py | Provide HTTP health probe that validates backend availability for Docker HEALTHCHECK. | Bot ops | Bot restart |
| modify | frontend/Dockerfile | Split dependency install/runtime, run dev server as non-root, and add curl-based health probe. | Frontend dev infra | Yes (rebuild frontend image) |
| modify | infra/docker-compose.yml | Invoke Celery via `/opt/venv/bin`, add explicit beat schedule path under `/app/run`, and pass `BOT_HEALTHCHECK_URL` for explicit probe target. | Compose | Restart celery/bot |
| modify | docs/codex/CHANGELOG.codex.md | Reference container hardening milestone for traceability. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Log container hardening artefacts per Codex journal policy. | Docs | No |

## 2025-11-08 – codex/docs/full-audit (pending)

**Summary:** Recorded repository-wide security & quality audit baseline and published CODEX_AUDIT_REPORT.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | CODEX_AUDIT_REPORT.md | Publish reproducible audit report and findings register. | Cross-cutting | No |
| modify | docs/codex/DIFF.codex.md | Log audit artefact creation per Codex journal requirements. | Docs | No |
| modify | docs/codex/CHANGELOG.codex.md | Reference audit milestone for future PRs. | Docs | No |


## 2025-11-13 – codex/infra/database-connection-pooling (pending)

**Summary:** Install PgBouncer in the compose stack, tune Django/Celery to reuse pooled
connections, move sessions into Redis-backed cache, and slow down admin log polling so
Postgres stops exhausting `max_connections`.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | infra/pgbouncer/pgbouncer.ini | Provide transaction-pooling defaults (session auth, timeouts) for PgBouncer service. | Infra database | Restart backend & PgBouncer |
| create | infra/pgbouncer/userlist.txt | Ship md5 credentials for local postgres user so PgBouncer can authenticate connections. | Infra database | Restart backend & PgBouncer |
| modify | infra/docker-compose.yml | Add PgBouncer service, route backend/Celery via 6432, expose Redis URL and worker caps, and pin to the supported `edoburu/pgbouncer:v1.24.1-p1` image after Docker Hub rejected `pgbouncer/pgbouncer:1.23.0`. | Infra orchestration | Restart backend & workers |
| modify | backend/nutribot/settings.py | Enable connection health checks, disable server-side cursors, add Redis/LocMem session cache. | Backend runtime | Restart backend |
| modify | backend/entrypoint.sh | Honour WEB_* env caps when starting gunicorn to limit worker/thread fan-out. | Backend runtime | Restart backend |
| modify | backend/apps/monitoring/admin.py | Run stream view outside transactions and close DB connections after serialising JSON. | Admin backend | Restart backend |
| modify | backend/apps/monitoring/templates/admin/monitoring/applicationlog/console.html | Default console polling to paused state, add interval selector, and reschedule timers safely. | Admin UI | No |
| modify | backend/apps/market/api/events.py | Close DB connections before/after SSE streaming and mark view as non-atomic. | Backend realtime API | Restart backend |
| modify | docs/codex/CHANGELOG.codex.md | Log the database connection pooling hardening per Codex changelog rules. | Docs | No |
| modify | docs/codex/DECISIONS.md | Record the decision referencing ADR for pooling and log throttling. | Docs | No |
| create | docs/codex/adr/2025-11-13-database-connection-pooling.md | Capture rationale/alternatives for PgBouncer + admin throttling. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Register this audit entry. | Docs | No |

## 2025-11-14 – codex/frontend/market-mealplans-polish (pending)

**Summary:** Surface marketplace meal plan programs on the hub page and tighten the mobile experience of the dedicated listing with responsive filters.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/market/MarketHubPage.tsx | Highlight published meal plan programs above recipe collections on the marketplace hub. | Frontend UX | No |
| modify | frontend/src/pages/market/MarketMealPlansPage.tsx | Rework search, filter, and slider layout to prevent horizontal scrolling on mobile and match marketplace styling. | Frontend UX | No |
| modify | frontend/src/components/ui/SegmentedControl.tsx | Allow toggle groups to wrap and stretch items for compact responsive filters. | Frontend UI kit | No |

## 2025-11-13 – codex/fullstack/market-mealplan-programs (pending)

**Summary:** Launch marketplace catalogue for expert meal plan programs with goal/tag metadata, nutrition metrics aggregation, public filters, and dedicated SPA listing/detail pages.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/models.py | Add goal, tags, duration, and calorie fields with normalization logic for marketplace plans. | Backend schema | Yes (market.0007) |
| create | backend/apps/market/migrations/0007_mealplan_goal_tags.py | Persist new meal plan goal/tag/calorie fields and supporting indexes. | Backend schema | Yes (market.0007) |
| create | backend/apps/market/services/meal_plan_metrics.py | Provide reusable nutrition aggregation helpers and stat sync utilities. | Backend services | No |
| modify | backend/apps/market/services/meal_plan_export.py | Reuse metrics helpers when exporting plans and enrich payloads. | Backend services | No |
| modify | backend/apps/market/serializers.py | Expose new goal/tag/calorie fields in API responses. | Backend API | No |
| modify | backend/apps/market/filters.py | Add goal/duration/calorie filters with SQLite-safe tag matching. | Backend API | No |
| modify | backend/apps/market/views.py | Wire marketplace plan ordering, filters, and relaxed detail access. | Backend API | No |
| modify | backend/apps/market/signals.py | Sync plan stats on save via metrics helpers. | Backend services | No |
| modify | backend/apps/market/admin.py | Surface new goal/tag/calorie fields in admin. | Backend admin | No |
| modify | backend/apps/market/tests/test_meal_plan_api.py | Cover new filters, field exposures, and stats assertions. | Backend tests | No |
| modify | frontend/src/App.tsx | Register marketplace meal plan routes. | Frontend routing | No |
| modify | frontend/src/features/market/constants.ts | Add navigation entry for meal plan programs. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/api.ts | Support new query filters for marketplace plans. | Frontend API | No |
| modify | frontend/src/types/meal-plan.ts | Extend DTOs with goal, tags, duration, and calorie fields. | Frontend types | No |
| create | frontend/src/features/market/cards/MealPlanCard.tsx | Display marketplace meal plan summary card with pricing and stats. | Frontend UX | No |
| create | frontend/src/pages/market/MarketMealPlansPage.tsx | Implement marketplace listing with filters and infinite scrolling. | Frontend UX | No |
| create | frontend/src/pages/market/MarketMealPlanDetailPage.tsx | Show plan overview, calendar preview, and CTA on detail view. | Frontend UX | No |
| modify | docs/codex/CHANGELOG.codex.md | Record meal plan marketplace milestone. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append audit entry for meal plan marketplace changes. | Docs | No |

## 2025-11-12 – codex/fullstack/market-premium (pending)

**Summary:** Enable premium recipe and meal plan purchases via Stars wallet debits, gate content delivery, and surface pricing cues across API and SPA.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/models.py | Add `RecipeAccess` / `MealPlanAccess` models with helpers for entitlement checks. | Backend schema | Yes (market.0006) |
| create | backend/apps/market/migrations/0006_mealplanaccess_recipeaccess.py | Persist premium access tables and related constraints. | Backend schema | Yes (market.0006) |
| modify | backend/apps/market/serializers.py | Expose Stars pricing, premium flags, and entitlement fields in API payloads. | Backend API | No |
| modify | backend/apps/market/services/__init__.py | Re-export premium purchase helpers for view usage. | Backend services | No |
| modify | backend/apps/market/services/search.py | Include premium price/access markers in marketplace search results. | Backend API | No |
| create | backend/apps/market/services/premium.py | Centralise premium pricing, entitlement checks, and wallet-charged purchase flows. | Backend services | No |
| modify | backend/apps/market/views.py | Gate detail endpoints, add purchase actions, and allow wallet-charged access grants. | Backend API | No |
| create | backend/apps/market/tests/test_premium_access.py | Cover happy/insufficient balance flows and entitlement persistence. | Backend tests | No |
| modify | docs/codex/DIFF.codex.md | Record premium monetisation touchpoints. | Docs | No |
| create | docs/codex/CHANGELOG.codex.md | Summarise premium monetisation milestone. | Docs | No |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Show premium badges, Stars pricing, and purchase CTA handling. | Frontend UX | No |
| modify | frontend/src/features/market/cards/RecipeCard.stories.tsx | Update Storybook fixtures with premium pricing scenarios. | Frontend UX | No |
| modify | frontend/src/features/market/cards/CardComponents.test.tsx | Adjust card tests for new premium props and assertions. | Frontend tests | No |
| modify | frontend/src/features/meal-plans/components/PlanListCard.tsx | Surface premium flagging and pricing for meal plans. | Frontend UX | No |
| modify | frontend/src/types/market.ts | Extend recipe DTOs with premium access and pricing fields. | Frontend types | No |
| modify | frontend/src/types/meal-plan.ts | Extend meal plan DTOs with premium access and pricing fields. | Frontend types | No |

## 2025-11-08 – codex/fullstack/market-reviews (pending)

**Summary:** Introduce cross-entity review system with eligibility checks, averaged ratings, and SPA surfaces for stores, products, recipes, and meal plans.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/reviews/__init__.py | Register `apps.reviews` package for Django discovery. | Backend API | No |
| create | backend/apps/reviews/apps.py | Configure app startup and signal wiring. | Backend API | No |
| create | backend/apps/reviews/models.py | Persist review entries with generic FK, author, rating, and timestamps. | Backend schema | No |
| create | backend/apps/reviews/targets.py | Centralise model alias resolution for serializers/views. | Backend API | No |
| create | backend/apps/reviews/services.py | Aggregate ratings and sync metadata.rating/metadata.rating_count. | Backend services | No |
| create | backend/apps/reviews/eligibility.py | Enforce purchase/plan interaction rules before accepting reviews. | Backend services | No |
| create | backend/apps/reviews/serializers.py | Validate review payloads, prevent duplicates, and hydrate targets. | Backend API | No |
| create | backend/apps/reviews/views.py | Expose list/create endpoints with logging and eligibility checks. | Backend API | No |
| create | backend/apps/reviews/urls.py | Register REST routes under `/api/reviews/`. | Backend API | No |
| create | backend/apps/reviews/signals.py | Recalculate ratings on review create/delete. | Backend services | No |
| create | backend/apps/reviews/migrations/0001_initial.py | Create `reviews_review` table and supporting indexes. | Backend schema | Yes (reviews.0001) |
| create | backend/apps/reviews/tests/__init__.py | Enable pytest package discovery for reviews app. | Backend tests | No |
| create | backend/apps/reviews/tests/test_reviews_api.py | Cover eligibility, duplicate protection, and metadata sync. | Backend tests | No |
| modify | backend/apps/market/models.py | Add `GenericRelation` hooks for stores/products/recipes/meal plans. | Backend schema | No |
| modify | backend/nutribot/settings.py | Add `apps.reviews` to installed apps. | Backend config | No |
| modify | backend/nutribot/urls.py | Mount `/api/reviews/` router. | Backend API | No |
| create | frontend/src/api/reviews.ts | Provide client helpers for listing/creating reviews. | Frontend API | No |
| create | frontend/src/features/reviews/components/ReviewsSection.tsx | Implement lazy-loaded review list and submission form. | Frontend UX | No |
| create | frontend/src/features/reviews/index.ts | Re-export reviews components for consumers. | Frontend UX | No |
| modify | frontend/src/features/market/cards/StoreCard.tsx | Surface review toggle beneath store metadata. | Frontend UX | No |
| modify | frontend/src/features/market/cards/ProductCard.tsx | Embed review section below purchase controls. | Frontend UX | No |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Allow recipe cards to reveal and capture reviews. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/PlanListCard.tsx | Show averaged ratings next to plan stats. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/PlanDescriptionCard.tsx | Append review section to plan summary view. | Frontend UX | No |
| modify | frontend/src/features/market/cards/CardComponents.test.tsx | Stub auth context and keep card snapshot tests passing. | Frontend tests | No |

## 2025-11-06 – codex/frontend/meal-plan-ux-bugfix (pending)

**Summary:** Fix duplicated key warnings in sheet overlays and restore scrollable viewport for the create-recipe dialog.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/ui/Sheet.tsx | Provide explicit keys for AnimatePresence children and force-mount overlay/content to eliminate duplicate key warnings on close. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/CreateRecipeDialog.tsx | Constrain modal height and enable overflow scrolling so long forms remain accessible on smaller screens. | Frontend UX | No |

## 2025-11-11 – codex/fullstack/meal-plan-professionals (pending)

**Summary:** Deliver structured plan description workflows with professional templates, monitoring reminders, and export endpoints for client, specialist, and tabular formats.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/services/plan_description.py | Normalize ADIME/NCP description schema for parsing and serialization. | Backend services | No |
| create | backend/apps/market/services/meal_plan_export.py | Generate client HTML, specialist JSON, and CSV exports leveraging structured descriptions. | Backend API | No |
| modify | backend/apps/market/views.py | Expose `/export/` action on meal plans with format routing and validation. | Backend API | No |
| modify | backend/apps/market/tests/test_meal_plan_api.py | Cover export happy path and access control across formats. | Backend tests | No |
| create | frontend/src/features/meal-plans/planDescription.ts | Define schema utilities for structured descriptions, follow-up parsing, and review reminders. | Frontend state | No |
| create | frontend/src/features/meal-plans/planTemplates.ts | Provide 8+ professional templates with goals, tone, and monitoring defaults. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/PlanDescriptionEditor.tsx | Implement sheet editor for ADIME fields, template application, and monitoring inputs. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/PlanDescriptionCard.tsx | Display structured summary, reminders, and export controls. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Wire editor trigger, export handler, and card integration into builder workflow. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/api.ts | Add client helper to download export artifacts with filename parsing. | Frontend API | No |
| modify | frontend/src/features/meal-plans/components/PlanListCard.tsx | Surface upcoming review reminders for quick scanning in list view. | Frontend UX | No |

## 2025-11-10 – codex/frontend-bot/meal-plan-preferences (pending)

**Summary:** Respect user allergies/exclusions in the recipe library UI with opt-out controls and propagate the same normalization to bot plan generation.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/features/meal-plans/components/RecipeLibrary.tsx | Filter recipe search results using profile allergies/exclusions, surface toggleable preference banner, and flag risky recipes when filters are disabled. | Frontend UX | No |
| modify | bot/services/planner.py | Normalize allergy/exclusion terms and apply substring matching when building auto-generated menus. | Bot logic | No |

## 2025-11-09 – codex/frontend/meal-plan-goals (pending)

**Summary:** Wire meal plan goal presets with automatic calorie/macronutrient recommendations and surface goal context in the planner UI.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | frontend/src/features/meal-plans/goals.ts | Define goal multipliers and macro distribution helpers for reuse across components. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/PlanGoalsCard.tsx | Add goal selector, recommendation button, and automatic target recalculation tied to user profile metrics. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Persist selected goals in metadata, pass profile context, and seed new plans with recommended targets. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/PlanSummaryCard.tsx | Display selected goal and calorie delta in the summary badge area. | Frontend UX | No |

## 2025-11-08 – codex/frontend/meal-plan-products (pending)

**Summary:** Enable adding marketplace products to meal plans, introduce quick recipe creation, and align planner UI cues.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/api/market.ts | Provide client helper for recipe creation used by the builder dialog. | Frontend API | No |
| create | frontend/src/features/meal-plans/components/CreateRecipeDialog.tsx | Modal form to capture simplified recipe details and post them to the market API. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/RecipeLibrary.tsx | Add resource tabs, product cards, and wire recipe creation flow with planner integration. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Accept generic library items, support product drag/drop, and reuse addition handler. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanItemCard.tsx | Differentiate recipes vs products with badges and neutral wording. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanCalendar.tsx | Update helper text to reflect product support. | Frontend UX | No |

## 2025-11-07 – codex/backend/meal-plan-tests (pending)

**Summary:** Extend meal plan API coverage for publishing transitions and product nutrition aggregation.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/tests/test_meal_plan_api.py | Add helpers and scenarios for publish toggles and product nutrition totals. | Backend tests | No |

## 2025-11-06 – codex/nutrition/meal-plan-builder (pending)

**Summary:** Extend meal plan backend schema & permissions and deliver the interactive nutrition planner UI with calendar, recipe search, and plan management.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/models.py | Add price fields for meal plans and supporting index. | Backend schema | Yes (market.0005) |
| modify | backend/apps/market/serializers.py | Enrich meal plan/item payloads with pricing, nutrition snapshots, and aggregates. | Backend API | No |
| modify | backend/apps/market/views.py | Allow public meal plan visibility and preload recipe/product context. | Backend API | No |
| modify | backend/apps/market/permissions.py | Permit safe read access to published plans. | Backend API | No |
| create | backend/apps/market/migrations/0005_mealplan_price_amount_mealplan_price_currency_and_more.py | Persist new meal plan monetary fields and index. | Backend schema | Yes (market.0005) |
| create | backend/apps/market/tests/test_meal_plan_api.py | Cover CRUD, public access rules, and nutrition aggregates for plans. | Backend tests | No |
| modify | frontend/package.json | Declare DnD and date utilities for the planner UI. | Frontend build | npm install |
| modify | frontend/package-lock.json | Lock dependency graph after installing new libraries. | Frontend build | npm install |
| modify | frontend/src/App.tsx | Register the meal plan builder route. | Frontend routing | No |
| create | frontend/src/types/meal-plan.ts | Define shared meal plan DTOs for the client. | Frontend types | No |
| create | frontend/src/features/meal-plans/api.ts | Client wrappers for meal plan and item endpoints. | Frontend API | No |
| create | frontend/src/features/meal-plans/hooks.ts | React Query hooks/mutations for meal plan operations. | Frontend state | No |
| create | frontend/src/features/meal-plans/constants.ts | Centralise meal type metadata for calendar rendering. | Frontend UX | No |
| create | frontend/src/features/meal-plans/utils.ts | Nutrition helpers for builder analytics. | Frontend UX | No |
| create | frontend/src/features/meal-plans/types.ts | Shareable slot type for DnD components. | Frontend types | No |
| create | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Core builder shell combining calendar, sidebar, and library. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/MealPlanCalendar.tsx | Render 3D weekly grid with droppable meal slots. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/MealPlanItemCard.tsx | Draggable card for plan items with serving control. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/PlanGoalsCard.tsx | Manual target editor for calories & macros. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/PlanListCard.tsx | Manage personal plan catalogue (select/create/delete). | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/PlanSummaryCard.tsx | Display plan totals and daily breakdown stats. | Frontend UX | No |
| create | frontend/src/features/meal-plans/components/RecipeLibrary.tsx | Search/drag recipes into calendar slots. | Frontend UX | No |
| create | frontend/src/pages/nutrition/MealPlanBuilderPage.tsx | Page entry point for the builder route. | Frontend routing | No |

## 2025-11-05 – worktree (pending)

**Summary:** Enable marketplace cart checkout to mint orders, handle wallet payments, and sync inventory & realtime updates.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/services/checkout.py | Implement transactional cart checkout, wallet payment integration, inventory updates, and SSE emission. | Backend API | No |
| modify | backend/apps/market/services/__init__.py | Re-export checkout service helpers for view usage. | Backend API | No |
| modify | backend/apps/market/serializers.py | Add checkout payload serializer and expose order currency choices. | Backend API | No |
| modify | backend/apps/market/views.py | Wire checkout endpoint, profile resolution, and response payload. | Backend API | No |
| create | backend/apps/market/tests/test_checkout.py | Cover checkout happy-path, wallet payment, and insufficient funds scenarios. | Backend tests | No |
| modify | backend/apps/orders/services/wallet.py | Allow RUB-denominated order creation alongside wallet currencies. | Backend billing | No |

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

## 2025-11-06 – work (pending)

**Summary:** Stabilise CaloCoin + Stars wallet tests by supplying conversion rates and ensuring checkout uses stubbed payment providers.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/orders/tests/test_wallet_and_orders.py | Seed CaloCoin rate for wallet summary expectations and reuse stubbed `PaymentService` for checkout/Stars flows to keep provider enabled in tests. | Backend tests | No |

## 2025-11-09 – codex/frontend-mealplans-professional (pending)

**Summary:** Surface communication tone and review timing in professional exports/cards so clinicians see ADIME cues and CSV payloads stay interoperable.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/services/meal_plan_export.py | Include communication tone in specialist JSON and table CSV metadata for richer ADIME context. | Backend exports | No |
| modify | backend/apps/market/tests/test_meal_plan_api.py | Extend export coverage to assert tone/review fields in CSV output. | Backend tests | No |
| modify | frontend/src/features/meal-plans/components/PlanDescriptionCard.tsx | Show communication tone and review date sections with localisation in plan summary. | Frontend UX | No |
## 2025-11-12 – codex/frontend/react-router-v7 (pending)

**Summary:** Upgraded the SPA routing stack to React Router v7, resolving splat route warnings and aligning nested market routes with the new resolution semantics.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/package.json | Adopt React Router v7 to eliminate future-flag warnings and prepare for v7 defaults. | Frontend routing | npm install |
| modify | frontend/package-lock.json | Regenerate lockfile with React Router v7 dependencies. | Frontend routing | npm install |
| modify | frontend/src/App.tsx | Drop splat usage for the market layout so nested routes resolve under v7 semantics. | Frontend routing | No |
| modify | docs/codex/DIFF.codex.md | Log React Router upgrade per Codex audit requirements. | Docs | No |

## 2025-11-12 – codex/frontend/meal-plan-workspace (pending)

**Summary:** Restructure meal plan workspace with responsive tabs, rich recipe previews, and consistent confirmation dialogs.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/package.json | Declare Radix tabs dependency for new responsive workspace controls. | Frontend build | npm install |
| modify | frontend/package-lock.json | Lock dependency graph after installing tabs package. | Frontend build | npm install |
| create | frontend/src/components/ui/Tabs.tsx | Provide styled Radix tabs primitives aligned with UI kit tokens. | Frontend UX | No |
| create | frontend/src/components/ui/ConfirmDialog.tsx | Add reusable confirmation dialog component to replace native confirms. | Frontend UX | No |
| modify | frontend/src/components/ui/index.ts | Re-export new UI primitives for planner consumers. | Frontend UX | No |
| modify | frontend/src/api/market.ts | Expose recipe detail fetcher for modal presentation. | Frontend API | No |
| create | frontend/src/features/meal-plans/components/RecipeDetailsDialog.tsx | Display full recipe context in modal with add-to-plan action. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/RecipeLibrary.tsx | Wire detail modal triggers, persist state, and reuse new dialog. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/PlanListCard.tsx | Swap `window.confirm` for consistent ConfirmDialog workflow. | Frontend UX | No |
| modify | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Introduce responsive workspace tabs and reuse modal-driven flows. | Frontend UX | No |

## 2025-11-12 – codex/frontend/meal-plan-builder-empty-loop (pending)

**Summary:** Stop the meal plan builder from repeatedly re-rendering when no plans are loaded by guarding empty state resets and reusing a constant fallback list.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/features/meal-plans/components/MealPlanBuilder.tsx | Avoid reallocating empty selections while the plans query resolves to prevent infinite update depth errors. | Frontend UX | No |
| modify | docs/codex/DIFF.codex.md | Record the meal plan builder state loop fix per Codex audit requirements. | Docs | No |

## 2025-11-12 – codex/fullstack/market-premium (pending)

**Summary:** Enable premium marketplace content monetisation with wallet debits, access tracking, and Star-based UI indicators.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/services/premium.py | Implement premium pricing helpers, wallet debits, and access checks. | Backend billing | No |
| create | backend/apps/market/migrations/0006_mealplanaccess_recipeaccess.py | Persist recipe/plan access ledgers linked to wallet transactions. | Backend schema | Yes (market.0006) |
| create | backend/apps/market/tests/test_premium_access.py | Cover wallet top-up, purchase, and access enforcement scenarios. | Backend tests | No |
| modify | backend/apps/market/models.py | Add RecipeAccess/MealPlanAccess models for premium entitlement tracking. | Backend schema | Yes (market.0006) |
| modify | backend/apps/market/services/__init__.py | Re-export premium helpers for view/serializer integration. | Backend services | No |
| modify | backend/apps/market/services/search.py | Surface premium flags and Star pricing in recipe search payloads. | Backend API | No |
| modify | backend/apps/market/serializers.py | Expose price_stars/has_access fields and enforce profile-aware access flags. | Backend API | No |
| modify | backend/apps/market/views.py | Require authentication, enforce access, and add purchase actions for recipes/plans. | Backend API | No |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Display Star pricing, free badges, and unlocked state for premium recipes. | Frontend UX | No |
| modify | frontend/src/features/market/cards/RecipeCard.stories.tsx | Align storybook fixtures with premium pricing props. | Frontend docs | No |
| modify | frontend/src/features/market/cards/CardComponents.test.tsx | Update mocks to reflect Star pricing fields and avoid NaN renders. | Frontend tests | No |
| modify | frontend/src/features/meal-plans/components/PlanListCard.tsx | Render Star price badges and free labels for meal plans. | Frontend UX | No |
| modify | frontend/src/types/market.ts | Extend recipe DTO with Star pricing and access flags. | Frontend types | No |
| modify | frontend/src/types/meal-plan.ts | Extend plan DTOs with Star pricing and entitlement flags. | Frontend types | No |
## 2025-12-04 – codex/bot/telemetry-logger-slot (pending)

**Summary:** Restore the Telegram bot container startup by declaring the
`TelemetryLogger._logger` slot so the dataclass initialiser can attach the
underlying stdlib logger while `slots=True` remains enabled.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/logkit.py | Declare `_logger` as a dataclass slot to avoid `AttributeError` during logger initialisation. | Bot runtime | Restart bot |
| modify | docs/codex/DIFF.codex.md | Record the telemetry logger slot fix per Codex policy. | Docs | No |

## 2025-12-05 – codex/frontend/webapp-base-path (pending)

**Summary:** Ensure the Telegram WebApp works when published under HTTPS
sub-paths by deriving the router basename from `WEBAPP_URL`, exposing the
calculated base path via the Vite build, and covering the helper logic with
unit tests.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/vite.config.ts | Derive the app base path from `WEBAPP_URL`, pass it to the client build, and expose a default constant. | Frontend build | Restart frontend |
| create | frontend/src/lib/basePath.ts | Centralise base-path sanitisation/inference so the SPA router can reuse consistent logic. | Frontend routing | No |
| create | frontend/src/lib/basePath.test.ts | Cover sanitisation, inference, and env overrides for the new base-path helper. | Frontend tests | No |
| modify | frontend/src/main.tsx | Feed the inferred basename into `BrowserRouter` so routes resolve under sub-path deployments. | Frontend routing | No |
| create | frontend/src/vite-env.d.ts | Declare the injected base-path constant and Vite env typing for TypeScript. | Frontend tooling | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the WebApp base-path fix per Codex policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Append this audit record. | Docs | No |

## 2025-12-07 – codex/infra/cloudpub-restore (pending)

**Summary:** Restore the CloudPub tunnel container and expose manual overrides
for the Vite dev-server allow list while keeping caloiq.ru as the primary
domain.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/docker-compose.yml | Reintroduce the CloudPub agent so local environments still publish the gateway through CloudPub. | Infra runtime | Restart CloudPub |
| modify | infra/.env.example | Document the CloudPub token placeholder and the optional dev-server host override without re-adding the retired domain. | Infra config | No |
| modify | frontend/vite.config.ts | Allow extra dev-server hosts via env and keep the legacy CloudPub host accessible to unblock existing Telegram sessions. | Frontend dev server | Restart frontend |
| modify | docs/codex/DIFF.codex.md | Record this rollback/fix entry per Codex policy. | Docs | No |

## 2025-12-08 – codex/frontend/remove-cloudpub-host (pending)

**Summary:** Drop the retired `adversely-congruent-viper` hostname from the
frontend dev-server allow list while documenting how to admit new CloudPub
domains via the environment.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/vite.config.ts | Remove the obsolete CloudPub host and point developers to `DEV_SERVER_ALLOWED_HOSTS` for any future tunnels. | Frontend dev server | Restart frontend |
| modify | docs/codex/DIFF.codex.md | Record the host cleanup per Codex audit policy. | Docs | No |

## 2025-12-06 – codex/fullstack/webapp-multi-url (pending)

**Summary:** Make the Telegram bot and SPA robust to comma-separated
`WEBAPP_URL` lists so Telegram keyboards always receive a single HTTPS URL and
the router basename stays rooted at the intended mini-app path.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/config.py | Parse `WEBAPP_URL` lists to expose a valid mini-app URL for keyboards and the chat menu. | Bot auth | Restart bot |
| create | bot/tests/test_config.py | Cover `WEBAPP_URL` parsing to prevent regressions in bot configuration. | Bot tests | No |
| modify | frontend/src/lib/basePath.ts | Ignore secondary entries when sanitising the router basename for SPA routing. | Frontend routing | No |
| modify | frontend/src/lib/basePath.test.ts | Assert sanitisation handles comma/newline separated inputs. | Frontend tests | No |
| modify | frontend/vite.config.ts | Reuse candidate parsing for build-time host/base path resolution and include all hosts in dev server allow list. | Frontend build | Restart frontend |
| modify | docs/codex/CHANGELOG.codex.md | Log the multi-domain `WEBAPP_URL` handling improvement. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this audit entry per Codex policy. | Docs | No |

## 2025-12-07 – codex/fullstack/telegram-rehydrate (pending)

**Summary:** Harden the Telegram auth replay path with guarded rehydrate
sendData, ensure reply keyboards are removed after successful confirmation, and
cover WebApp payload decoding edge cases in bot tests.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Guard rehydrate sendData to fire once per page load only when a fresh token is available, preventing duplicate bot messages. | Frontend auth | No |
| modify | bot/handlers/webapp_data.py | Remove reply keyboards after auth confirmation and accept exp/exp_at payload variants. | Bot auth | No |
| modify | bot/tests/test_webapp_data.py | Cover auth keyboard removal, exp-key handling, and invalid payload decoding to keep WebApp flows stable. | Bot tests | No |
| modify | docs/codex/DIFF.codex.md | Log the Telegram rehydrate/auth fixes per Codex audit policy. | Docs | No |

## 2025-11-15 – codex/fullstack/webapp-auth-ttl (pending)

**Summary:** Guarantee the Telegram WebApp always replays auth tokens to the
bot, document the dual-domain hosts, and extend bot session retention without
changing the configured `WEBAPP_URL` ordering.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Ensure auth payloads reuse the Telegram SDK user ID and resend stored tokens when the WebApp session is restored. | Frontend auth | No |
| modify | bot/config.py | Make the bot FSM TTL configurable via `BOT_SESSION_TTL_HOURS` so restarts no longer drop authorisation immediately. | Bot runtime | Restart bot |
| modify | bot/main.py | Apply the configurable TTL when initialising Redis storage for the FSM. | Bot runtime | Restart bot |
| modify | infra/.env.example | List both HTTPS domains in `ALLOWED_HOSTS` and surface the new TTL variable for local configuration. | Infra config | No |
| modify | docs/codex/DIFF.codex.md | Append this audit entry per Codex policy. | Docs | No |


## 2025-12-09 – codex/fullstack/telegram-ui-diagnostics (pending)

**Summary:** Polish the Telegram integration page with light/dark-ready skeletons, actionable toasts, accessibility labels, and
diagnostics that surface Mini App SDK state and the last `sendData` attempt for reliable deep-link onboarding.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Add skeleton loaders, deep-link toast handling, and environment diagnostics including last sendData RID. | Frontend UI/diagnostics | No |
| modify | frontend/src/components/integrations/TelegramHeroCard.tsx | Improve CTA accessibility for Mini App/Telegram launch buttons. | Frontend UI | No |
| modify | frontend/src/components/integrations/TelegramStatusCard.tsx | Provide clipboard toasts and aria labels for deep-link regeneration and copy actions. | Frontend UI | No |
| modify | frontend/src/components/integrations/TelegramChatShell.tsx | Add toasts for bridge failures, SSE error notices, accessibility labels, and clarify the server-bridge chat disclaimer. | Frontend UI | No |
| modify | frontend/src/lib/telegram.ts | Track the last sendData attempt to expose RID/status in diagnostics. | Frontend auth telemetry | No |
| modify | docs/codex/DIFF.codex.md | Record this audit entry per Codex policy. | Docs | No |

## 2025-12-10 – codex/fullstack/telegram-bridge-sse (pending)

**Summary:** Deliver Telegram chat-shell events over Redis-backed SSE with
rate-limited bridge sends, bot-side pub/sub emission, and resilient EventSource
reconnects plus smooth client scrolling.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/users/telegram_integration.py | Add Redis pub/sub streaming, delivery status events, and rate limiting for the Telegram bridge send/stream endpoints. | Backend API | No |
| create | bot/services/bridge.py | Provide a reusable Redis publisher for Telegram bridge events. | Bot runtime | Restart bot |
| create | bot/middlewares/bridge.py | Emit sanitized Telegram update snippets into the bridge channel for SSE delivery. | Bot runtime | Restart bot |
| modify | bot/main.py | Register the bridge middleware and close the publisher on shutdown. | Bot runtime | Restart bot |
| create | bot/tests/test_bridge_middleware.py | Cover bridge middleware publishing behavior and empty-message filtering. | Bot tests | No |
| modify | frontend/src/components/integrations/TelegramChatShell.tsx | Reconnect EventSource streams, keep optimistic UI scroll in sync, and handle stream outages gracefully. | Frontend UI | No |
| modify | docs/codex/DIFF.codex.md | Record this SSE/chat-bridge enhancement per Codex audit policy. | Docs | No |

## 2025-12-11 – codex/backend/telegram-bridge-compat (pending)

**Summary:** Make the Telegram bridge resilient when optional dependencies are absent, reuse user-level telegram_id fallbacks, and
gracefully handle malformed Mini App payloads.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/users/telegram_integration.py | Degrade Redis/httpx/token masking imports gracefully, reuse user.telegram_id fallbacks, and harden logging. | Backend API | No |
| modify | bot/handlers/webapp_data.py | Capture JSON decode errors from WebApp payloads and surface diagnostics without crashing handlers. | Bot handler | No |

## 2025-12-12 – codex/fullstack/telegram-bridge-docs (pending)

**Summary:** Clarify Telegram status payloads and document SSE token-in-query trade-offs with logging guidance for the chat bridge.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | backend/apps/users/telegram_integration.py | Rename status usernames to app/Telegram variants to avoid confusion and keep linkage detection intact. | Backend API | No |
| modify | frontend/src/api/telegram.ts | Reflect status payload username fields for the integration UI. | Frontend API types | No |
| modify | frontend/src/components/integrations/TelegramStatusCard.tsx | Surface app vs Telegram usernames in diagnostics to match backend payloads. | Frontend UI | No |
| modify | docs/codex/DIFF.codex.md | Record the documentation and payload adjustments per Codex policy. | Docs | No |
| modify | docs/codex/CHANGELOG.codex.md | Log the chat-bridge token-in-query note and status payload rename. | Docs | No |

**Notes:** SSE authentication for the Telegram chat bridge continues to rely on JWT in the query-string for EventSource
compatibility. Mask query components in reverse-proxy access logs (e.g., `$request_uri` without args or custom filters) to avoid
token leakage in log stores.

## 2025-12-13 – codex/infra/webapp-url-path (pending)

**Summary:** Align the default WebApp URL with the `/auth-bridge` path so Mini App launches provide Telegram initData for
sendData-based auto-auth.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/.env.example | Default the WebApp URL to `/auth-bridge` so bot keyboards launch the Mini App context with initData. | Infrastructure defaults | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the WebApp URL path alignment per Codex audit policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Log this infra default change for traceability. | Docs | No |

## 2025-12-14 – codex/fullstack/telegram-startapp-link (pending)

**Summary:** Separate startapp deeplinks from the WebApp URL, propagate the bot username to the frontend, and ensure CTA/auth flows always launch the Mini App context.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/deeplinks.ts | Centralise the bot username from env and build start/startapp links without hardcoded defaults. | Frontend deeplinks | Rebuild frontend |
| modify | frontend/src/pages/AuthBridge.tsx | Fall back to startapp deeplinks (with bot username) when redirecting from a non-WebApp context. | Frontend auth | No |
| modify | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Always open Mini App via startapp deeplinks for CTAs and Telegram login buttons. | Frontend UI | No |
| modify | infra/.env.example | Document bot username env variables for link generation and bot menus. | Infra config | No |
| modify | infra/docker-compose.yml | Pass the bot username into the frontend build for consistent deeplinks. | Frontend build | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Log the startapp/WebApp URL separation per audit policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this audit entry per Codex policy. | Docs | No |

## 2025-12-15 – codex/fullstack/telegram-runtime-auth-bridge (pending)

**Summary:** Enforce Mini App runtime detection before auth, add a reusable auth-bridge helper, and make Telegram CTAs reuse it to avoid sendData calls outside the WebApp context.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Add strict initData validation, export a reusable runAuthBridge helper, and redirect to startapp deeplinks when not in Mini App runtime. | Frontend auth | No |
| modify | frontend/src/pages/AuthBridge.tsx | Use the runtime-aware auth bridge with Telegram status payloads for deterministic Mini App login. | Frontend auth | No |
| modify | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Wire the "Авторизоваться" CTA through the auth bridge so Mini App sessions exchange tokens instead of reopening links. | Frontend UI/auth | No |
| modify | docs/codex/CHANGELOG.codex.md | Log the runtime-gated auth bridge per Codex audit policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this audit entry per Codex policy. | Docs | No |

## 2025-12-16 – codex/fullstack/telegram-deeplink-compat (pending)

**Summary:** Restore backward compatibility for Telegram deeplink builders so legacy call signatures don't swap payloads and bot usernames.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/deeplinks.ts | Detect legacy vs new argument order for start/startapp link builders to avoid broken Mini App URLs. | Frontend deeplinks | Rebuild frontend |
| modify | docs/codex/CHANGELOG.codex.md | Log the deeplink signature compatibility fix per Codex audit policy. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this audit entry per Codex policy. | Docs | No |

## 2025-12-17 – codex/frontend/telegram-senddata-desktop-reliability (pending)

**Summary:** Add delivery cushions and a Telegram Desktop fallback button so auth sendData has time to arrive before closing the WebApp.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Add delivery pauses around sendData/close and a Telegram Desktop fallback MainButton to retry auth payloads. | Frontend auth bridge | No |
| modify | docs/codex/DIFF.codex.md | Record the Telegram auth sendData reliability adjustments per Codex policy. | Docs | No |

## 2025-12-18 – codex/frontend/telegram-mainbutton-handler (pending)

**Summary:** Fix Telegram Desktop manual auth fallback by wiring MainButton click handlers through the official onEvent API and surfacing click logs.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Attach/detach Telegram MainButton handlers via onEvent/offEvent with logging so Desktop fallback clicks resend auth payloads. | Frontend auth bridge | No |
| modify | docs/codex/DIFF.codex.md | Log the MainButton click handler fix per Codex audit policy. | Docs | No |
## 2025-12-12 – codex/telegram-inline-webapp (pending)

**Summary:** Removed the deprecated sendData/web_app_data flow for inline Mini Apps, shifted the WebApp login to server-side confirmation via answerWebAppQuery, and cleaned frontend diagnostics to focus on initData runtime state.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | frontend/src/lib/telegram.ts | Drop sendData/rehydrate logic, reuse initData exchange for the auth bridge, and keep token storage local without bot delivery. | Frontend auth | Rebuild frontend |
| modify | frontend/src/pages/integrations/TelegramIntegrationPage.tsx | Simplify diagnostics to initData/runtime flags and remove sendData expectations. | Frontend UI | Rebuild frontend |
| modify | frontend/src/components/integrations/TelegramHowItWorks.tsx | Refresh step copy to describe inline initData + backend confirmation. | Frontend UI | Rebuild frontend |
| modify | backend/apps/auth/views.py | Send answerWebAppQuery on successful inline auth using the validated query_id. | Backend auth | Restart backend |
| modify | backend/apps/users/tg_auth.py | Surface query_id from initData, persist it in exchange responses, and call answerWebAppQuery with audit logging. | Backend auth | Restart backend |
| modify | bot/main.py | Unregister the obsolete web_app_data handler to avoid silent sendData waits. | Bot runtime | Restart bot |
| delete | bot/handlers/webapp_data.py | Remove the web_app_data router now that inline Mini Apps use answerWebAppQuery. | Bot runtime | Restart bot |
| delete | bot/tests/test_webapp_data.py | Drop tests covering the removed web_app_data handler. | Bot tests | No |
| modify | docs/codex/DIFF.codex.md | Record the inline WebApp sendData removal and backend confirmation path. | Docs | No |

## 2025-12-19 – codex/fullstack/telegram-session-store (pending)

**Summary:** Persist Telegram Mini App JWTs server-side, expose a bot-key-guarded session endpoint, and hydrate the bot FSM from backend tokens instead of sendData.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | backend/apps/users/migrations/0012_telegramsession.py | Add DB storage for Telegram access/refresh tokens. | Backend auth | Run migration + restart backend |
| modify | backend/apps/users/models.py | Introduce TelegramSession model linked to Profile. | Backend auth | Restart backend |
| modify | backend/apps/users/tg_auth.py | Store exchanged JWTs in TelegramSession and stop returning tokens to the client. | Backend auth | Restart backend |
| modify | backend/apps/users/views.py | Add get_telegram_session endpoint refreshing expired access tokens with bot-key auth. | Backend API | Restart backend |
| modify | backend/apps/users/urls.py | Wire bot/telegram/session route under /api/users/. | Backend routing | Restart backend |
| modify | backend/nutribot/settings.py | Load TELEGRAM_BOT_KEY for bot-key-protected endpoints. | Backend config | Restart backend |
| create | backend/apps/users/tests/test_telegram_session_endpoint.py | Cover bot-key auth, token retrieval, and refresh on expiry. | Backend tests | No |
| modify | backend/tests/test_tg_exchange.py | Align initData HMAC to WebApp scheme and assert server-side token persistence. | Backend tests | No |
| modify | backend/tests/test_webapp_login.py | Use WebApp initData signatures for login flow expectations. | Backend tests | No |
| modify | bot/backend_client.py | Fetch Telegram sessions via bot-key-secured backend endpoint. | Bot backend client | Restart bot |
| modify | bot/middlewares/access_token.py | Hydrate FSM tokens from backend Telegram sessions when absent. | Bot middleware | Restart bot |
| create | bot/tests/test_access_token_middleware.py | Verify middleware skips backend when token exists and stores fetched sessions. | Bot tests | No |
| modify | docs/codex/CHANGELOG.codex.md | Log Telegram session storage and bot hydration changes. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Record this change set per Codex policy. | Docs | No |

## 2025-12-20 – codex/bot/webhook-mode (pending)

**Summary:** Enable aiogram webhook mode end-to-end with environment toggles while preserving polling fallback.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/config.py | Load webhook settings (enable flag, URL, secret, port, path) from environment for aiogram 3.22+. | Bot config | Restart bot |
| modify | bot/main.py | Switch dispatcher startup between webhook and polling, configure aiohttp webhook server, and clean shutdown with webhook deletion. | Bot runtime | Restart bot |
| modify | docs/codex/DIFF.codex.md | Log the webhook enablement change set per Codex audit policy. | Docs | No |

## 2025-12-23 – codex/bot/webhook-config-cleanup (pending)

**Summary:** Stop nulling webhook secrets, require explicit HTTPS webhook URLs before enabling webhook mode, and enrich fallback
logging with path/port/update metadata to speed up debugging behind reverse proxies.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/config.py | Load webhook URL as-is (default empty) and keep WEBHOOK_SECRET untouched so header validation is not disabled. | Bot config | Restart bot |
| modify | bot/main.py | Reuse resolved webhook path/allowed updates in logs and webhook setup while logging HTTPS/fallback context. | Bot runtime | Restart bot |
| modify | infra/.env.example | Provide HTTPS webhook URL/secret hints without relying on code defaults. | Bot config | No |
| modify | docs/codex/DIFF.codex.md | Record the webhook configuration cleanup per Codex audit policy. | Docs | No |

## 2025-12-24 – codex/bot/webhook-observability (pending)

**Summary:** Add webhook request diagnostics (health probe and request logger) and ship an HTTPS Nginx config for caloiq.ru with strict POST-only forwarding to the bot.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | bot/main.py | Log inbound webhook requests with secret/header presence and expose /healthz for Nginx/Ingress probes. | Bot runtime | Restart bot |
| modify | infra/nginx.conf | Provide caloiq.ru HTTPS reverse proxy with POST-only /bot/webhook forwarding and bot health probe. | Infra | Reload Nginx |
| modify | docs/codex/DIFF.codex.md | Record webhook observability and Nginx config updates per Codex audit policy. | Docs | No |

## 2025-12-24 – codex/infra/letsencrypt-webroot-bootstrap (pending)

**Summary:** Align Let’s Encrypt bootstrap and renewal scripts with the webroot flow used by the gateway, avoiding downtime while keeping certbot/ACME paths consistent.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/bootstrap-ssl.sh | Bootstrap certificates via the shared webroot and start renewal/reloader services without stopping the gateway. | Infra | Restart gateway/certbot |
| modify | infra/renew-ssl.sh | Provide a manual webroot renew-and-reload helper consistent with the background certbot/reloader containers. | Infra | Reload gateway |

## 2025-12-25 – codex/bot/webhook-secret-example (pending)

**Summary:** Provide a stronger sample webhook secret to avoid reusing trivial defaults when configuring webhook deployments.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| modify | infra/.env.example | Replace the webhook secret hint with a realistic 32-character token to encourage unique secrets in deployments. | Bot config | No |

## 2025-12-23 – codex/infra/timeweb-letsencrypt (pending)


**Summary:** Added a dedicated ACME helper service that issues/renews Let's Encrypt
certificates through the Timeweb DNS API (DNS-01), stores them inside a shared
Docker volume, and documents how to trigger issuance/renewals while keeping the
gateway HTTP-only until we're ready to serve HTTPS locally.

| Action | Path | Reason | Impact | Migrations / Restart |
| --- | --- | --- | --- | --- |
| create | infra/acme/Dockerfile | Package certbot with the Timeweb DNS hook scripts so issuance runs in an isolated helper container. | Infra / TLS | Build `acme` image |
| create | infra/acme/entrypoint.sh | Route `issue`/`renew`/`cron` commands invoked via Compose into the right certbot workflow. | Infra / TLS | No |
| create | infra/acme/certbot-issue.sh | Automate first-time cert issuance (apex + wildcard + extras) with manual DNS hooks. | Infra / TLS | No |
| create | infra/acme/certbot-renew.sh | Wrap `certbot renew` with the Timeweb hooks so DNS-01 renewals run unattended. | Infra / TLS | No |
| create | infra/acme/renew-cron.sh | Keep the helper alive and retry renewals on a configurable interval when the acme profile is up. | Infra / TLS | Restart acme profile |
| create | infra/acme/timeweb_dns_hook.py | Talk to the Timeweb Cloud API to add/remove `_acme-challenge` TXT records and wait for propagation. | Infra / TLS | No |
| modify | infra/docker-compose.yml | Mount the shared `letsencrypt` volume on the gateway and register the optional `acme` service profile. | Infra | Restart gateway when mounting volume |
| modify | infra/.env.example | Document the required Timeweb/ACME secrets and toggles for the new helper. | Infra docs | No |
| create | docs/infra/letsencrypt.md | Explain environment variables, issuance, renewals, and cron usage for the Timeweb DNS-01 flow. | Docs | No |
| create | scripts/letsencrypt/issue.sh | Provide a repo-level helper to run `docker compose --profile acme run acme issue`. | Tooling | No |
| create | scripts/letsencrypt/renew.sh | Provide a helper for manual `certbot renew` runs via Compose. | Tooling | No |
| modify | docs/codex/CHANGELOG.codex.md | Record the Timeweb DNS-01 automation milestone. | Docs | No |
| modify | docs/codex/DIFF.codex.md | Add this traceability entry per Codex policy. | Docs | No |

