# Codex Diff Journal

## 2025-10-30 – commit TBD (market realtime hardening)

Summary: Stabilize the market realtime surface by serving a temporary events stub, hardening websocket transport, and guarding Telegram-only behaviors on the web client.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/views_events.py | Provide an authenticated placeholder response for `/api/v1/market/events/` so the SPA no longer receives 404 errors while the real feed is under construction. | backend | no |
| modify | backend/apps/market/urls.py | Register the events stub route alongside existing market routers. | backend | no |
| modify | backend/nutribot/settings.py | Normalize allowed host parsing, seed default CSRF origins, and default the channel layer to Redis to support websocket handshakes behind nginx. | backend | backend restart |
| modify | infra/nginx.conf | Add a dedicated `/ws/` location with Upgrade headers for Channels websocket traffic. | infra | nginx reload |
| modify | frontend/src/features/market/hooks/useMarketRealtime.ts | Skip the SSE poller unless an explicit `VITE_MARKET_EVENTS_URL` is configured, preventing spurious calls to the absent endpoint. | frontend | no |
| modify | frontend/src/lib/telegram.ts | Gate Telegram WebApp helpers behind init data checks and avoid invoking Mini App APIs in a regular browser. | frontend | no |
| modify | frontend/src/lib/monitoring.ts | Resolve init data through the safe Telegram guard to prevent bogus headers. | frontend | no |
| modify | frontend/src/pages/Orders.tsx | Require a verified Telegram Mini App context before wiring invoice handlers, reducing user-facing errors outside Telegram. | frontend | no |
| modify | frontend/src/pages/Feed.tsx | Disable vertical swipes only on supported Telegram versions and skip the call entirely when the Mini App context is absent. | frontend | no |
| modify | frontend/src/components/ui/Sheet.tsx | Switch to `motion.create` and assign explicit keys to eliminate Framer/React warnings. | frontend | no |
| modify | frontend/src/main.tsx | Opt into the React Router v7 future flags to silence migration warnings. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Record the market realtime hardening work at a high level. | docs | no |
| modify | docs/codex/DIFF.codex.md | Log the detailed artifact changes for this patch. | docs | no |

## 2025-10-30 – commit TBD (billing buttons ui kit)

Summary: Swap the billing actions to the new UI kit button component and delete the legacy `.orders-button` styles so dark and light themes render consistently.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/Orders.tsx | Replace legacy `<button>` markup with the shared Button component, add action state tracking, and wire loading indicators for billing operations. | frontend | no |
| modify | frontend/src/styles/components/buttons.css | Remove the `.orders-button` aliases now that the billing page uses the UI kit components exclusively. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Record the UI kit button migration for the billing actions. | docs | no |

## 2025-10-29 – commit TBD (grid shimmer dark override)

Summary: Lock the grid shimmer canvas palette to component-scoped values so the night theme no longer recolors the animation.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/GridShimmerCanvas.tsx | Apply component-only palette overrides and theme detection so the shimmer colors stay consistent in dark mode without touching global tokens. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Record the grid shimmer palette override for traceability. | docs | no |

## 2025-10-29 – commit TBD (auth legacy background)

Summary: Ensure legacy auth background canvases and logo colors reuse the scoped base stylesheet without timing glitches.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/hooks/useLegacyStyles.ts | Switch to an isomorphic layout effect and allow conditional activation so legacy CSS mounts before auth canvases read layout metrics. | frontend | no |
| modify | frontend/src/App.tsx | Mount legacy styles while showing auth routes so the background canvases and shared chrome reuse the restored stylesheet. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Log the auth background fix in the diff journal. | docs | no |

## 2025-10-29 – commit TBD

Summary: Restore legacy auth/profile/billing layouts by injecting their base styles only for the relevant routes.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | frontend/src/hooks/useLegacyStyles.ts | Inject legacy base.css dynamically with lifecycle control so classic pages regain styling without affecting the new UI kit. | frontend | no |
| create | frontend/src/types/assets.d.ts | Provide TypeScript typings for Vite inline CSS imports used by the legacy style injector. | frontend | no |
| modify | frontend/src/pages/Login.tsx | Load legacy styles on the login route to restore layout and segmented control formatting. | frontend | no |
| modify | frontend/src/pages/Register.tsx | Attach legacy styles for the registration form so validation and layout visuals return. | frontend | no |
| modify | frontend/src/pages/ForgotPassword.tsx | Reapply legacy visuals to the recovery flow while preserving new UI defaults elsewhere. | frontend | no |
| modify | frontend/src/pages/ResetPassword.tsx | Ensure reset forms mount legacy styling during token-based password updates. | frontend | no |
| modify | frontend/src/pages/Profile.tsx | Bring back the extensive profile sidebar/card styling by mounting the legacy stylesheet. | frontend | no |
| modify | frontend/src/pages/Orders.tsx | Restore billing/monetization cards and tables via scoped legacy styles. | frontend | no |
| modify | frontend/src/pages/Dashboard.tsx | Reinstate daily plan cards and forms with legacy styling injection. | frontend | no |
| modify | frontend/src/styles/index.css | Remove the global base.css import since styles now load on demand per page. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Record scoped legacy style restoration for traceability. | docs | no |

## 2025-10-28 – commit TBD

Summary: Modernize the sticky navigation bar interactions and neutralize control styling for the 2025 design refresh.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/nav/AppNavbar.tsx | Rework sticky reveal/hide logic and restyle navigation controls with neutral theming. | frontend | no |
| modify | frontend/src/components/nav/ThemeToggle.tsx | Harmonize theme switcher visuals with the updated neutral palette and improve dark/light legibility. | frontend | no |

## 2025-10-27 – commit d9ebc28

Summary: Align the frontend UI with the refreshed design tokens and theme system from the new UI kit.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/styles/index.css | Import tokens, define derived variables, and replace legacy palette values with token-driven mixes. | frontend | no |
| modify | frontend/src/pages/ResetPassword.tsx | Use design-token feedback colors. | frontend | no |
| modify | frontend/src/pages/Register.tsx | Apply token-based status colors for validation messaging. | frontend | no |
| modify | frontend/src/pages/Dashboard.tsx | Sync inline colors and separators with new palette. | frontend | no |
| modify | frontend/src/pages/Login.tsx | Replace hard-coded error tint with token color. | frontend | no |
| modify | frontend/src/pages/ForgotPassword.tsx | Align async states with token colors. | frontend | no |
| modify | frontend/src/ui/MenuCard.tsx | Move tag, border, and feedback styling to token palette. | frontend | no |
| modify | frontend/src/test/mocks/auth.ts | Use tokenized avatar accent. | frontend | no |
| modify | frontend/src/lib/telegram.ts | Respect global background token for Telegram WebApp shell. | frontend | no |
| modify | frontend/src/api/api.ts | Provide macro colors via theme tokens for UI consumers. | frontend | no |
| modify | frontend/src/components/ProfileSidebar.tsx | Recolor gradients and badges using token-driven variables. | frontend | no |
| modify | frontend/src/components/Logo.tsx | Bind SVG fills and strokes to logo token tones. | frontend | no |
| modify | frontend/src/utils/avatar.ts | Express preset gradients via theme variables. | frontend | no |
| modify | frontend/src/components/GridShimmerCanvas.tsx | Resolve glow/base colors from CSS tokens and react to theme changes. | frontend | no |
| create | docs/codex/DIFF.codex.md | Record traceability for the UI kit migration. | docs | no |

## 2025-10-27 – commit HEAD

Summary: Tokenize component color usage, harden linting against new literals, and add accessibility coverage for button variants.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/styles/tokens.css | Expand shared token palette with derived canvas/brand variables for component consumption. | frontend | no |
| modify | frontend/src/components/Logo.tsx | Bind SVG fills and strokes to shared brand tokens. | frontend | no |
| modify | frontend/src/components/ProfileSidebar.tsx | Replace gradient and badge literals with CSS custom properties. | frontend | no |
| modify | frontend/src/components/GridShimmerCanvas.tsx | Resolve animation palette from CSS variables and observe theme changes. | frontend | no |
| modify | frontend/src/components/GlowingLineCloudsCanvas.tsx | Probe runtime theme colors for framer-motion strokes and glows. | frontend | no |
| modify | frontend/src/components/ui/Button.tsx | Align button variants with tokenized classes and normalize motion props. | frontend | no |
| create | frontend/src/components/ui/__tests__/Button.accessibility.test.tsx | Add vitest + axe suite validating token-driven focus states and shadows. | frontend | no |
| create | frontend/eslint.config.mjs | Introduce ESLint flat config banning new color literals in components. | frontend | no |
| modify | frontend/package.json | Wire lint rule into workflows via lint/test scripts. | frontend | no |
| modify | frontend/package-lock.json | Capture dependency graph for new lint/test tooling. | frontend | no |

## 2025-10-27 – commit 56fcf02

Summary: Resolve duplicate keys in the sheet component and align base form controls with the UI kit token system.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/ui/Sheet.tsx | Add explicit keys to overlay and content for AnimatePresence to eliminate duplicate key warnings. | frontend | no |
| modify | frontend/src/styles/index.css | Update base element styles to consume UI kit tokens exclusively and refine default interactions. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Document the follow-up adjustments to the UI kit migration. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the additional frontend and documentation updates. | docs | no |
