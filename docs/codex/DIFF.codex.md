# Codex Diff Journal

## 2025-11-12 – commit TBD (market filters ordering + rating support)

Summary: Enabled DRF ordering and rating/protein/price filters across marketplace APIs, added JSONB indexes for metadata lookups, aligned SPA filter configuration with backend capabilities, and expanded API/UI test coverage.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/filters.py | Centralize parsing and application of marketplace filter params reused by viewsets and search service. | backend | no |
| modify | backend/apps/market/views.py | Wire DRF `OrderingFilter`, call shared filters, and expose rating/protein/price constraints on listings. | backend | no |
| modify | backend/apps/market/services/search.py | Respect min rating/protein/max price filters and reuse shared coercion helpers. | backend | no |
| modify | backend/apps/market/models.py | Declare JSONB GIN indexes for metadata-driven queries. | backend | yes – apply migration 0003 |
| create | backend/apps/market/migrations/0003_market_metadata_indexes.py | Create metadata GIN indexes on Postgres while keeping sqlite-compatible state. | backend | yes – `python manage.py migrate apps.market 0003` |
| modify | backend/nutribot/settings.py | Enable `django.contrib.postgres` for GIN index support. | backend | yes – reload app |
| modify | backend/apps/market/tests/test_search_api.py | Cover rating/protein/price filters within the search endpoint. | backend | no |
| create | backend/apps/market/tests/test_filters_api.py | Assert ordering/min-rating and protein/price filters on REST collections. | backend | no |
| create | frontend/src/features/market/filters/config.ts | Provide shared filter/sort configuration and ordering map for the SPA. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.tsx | Consume shared config instead of local constants. | frontend | no |
| modify | frontend/src/features/market/constants.ts | Re-export filter types/constants from the new config module. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Map sort options to backend ordering params and emit numeric filters. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.test.tsx | Verify quick filters/rating propagate to API calls. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Log this diff entry for traceability. | docs | no |

## 2025-11-11 – commit TBD (market card flat fields)

Summary: Flattened marketplace serializers to expose store/product/recipe metadata, optimized queryset prefetching, refreshed SPA typings and card rendering to avoid NaN placeholders, and covered the new contract with backend and frontend tests.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/serializers.py | Expose flattened metadata fields and numeric conversions for stores, products, and recipes. | backend | no |
| modify | backend/apps/market/views.py | Prefetch related store/owner/inventory data to support the enriched serializers without N+1 queries. | backend | no |
| create | backend/apps/market/tests/test_viewsets_serialization.py | Assert the flattened API payloads for stores, products, and recipes. | backend | no |
| modify | frontend/src/types/market.ts | Align marketplace resource typings with the expanded backend payload. | frontend | no |
| modify | frontend/src/features/market/cards/ProductCard.tsx | Guard against NaN display, use flattened fields, and surface reliable pricing data. | frontend | no |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Normalize macro and price rendering using the flattened metadata fields. | frontend | no |
| modify | frontend/src/features/market/cards/StoreCard.tsx | Harden delivery/rating formatting against invalid values. | frontend | no |
| create | frontend/src/features/market/cards/CardComponents.test.tsx | Provide regression tests ensuring cards render without NaN artifacts. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Log this diff entry for traceability. | docs | no |

## 2025-11-10 – commit TBD (market events SSE proxy)

Summary: Delivered a JWT-protected `/api/v1/market/events/` SSE proxy, renamed the frontend subscription hook, documented the contract, and captured local load-test metrics.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/api/events.py | Expose a dedicated SSE proxy that filters `market.*` events and forwards keepalives. | backend | no |
| modify | backend/apps/market/api/__init__.py | Re-export the events view for URL wiring. | backend | no |
| modify | backend/apps/market/urls.py | Register `/v1/market/events/` under the market namespace. | backend | no |
| create | backend/apps/market/tests/test_events_api.py | Cover auth failures, resource validation, and SSE filtering. | backend | no |
| move | frontend/src/features/market/hooks/useMarketRealtime.ts → frontend/src/features/market/hooks/useMarketEvents.ts | Rename and harden the client hook around the new endpoint. | frontend | no |
| modify | frontend/src/features/market/hooks/useMarketEvents.ts | Improve reconnect logic, keepalive handling, and naming. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Point the marketplace page at the renamed hook. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.test.tsx | Update mocks to match the renamed hook. | frontend | no |
| create | docs/frontend/market/market-events-contract.md | Describe the SSE contract, authentication, and sanity load metrics. | docs | no |
| modify | docs/codex/CHANGELOG.codex.md | Record the realtime proxy milestone. | docs | no |
| modify | docs/codex/DIFF.codex.md | Log this diff entry. | docs | no |

## 2025-11-09 – commit TBD (market cart/plan submission endpoints)

Summary: Delivered sugar cart/plan submission endpoints, aligned the SPA forms and stores with the new contract, and added backend/frontend tests plus decision records.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | docs/codex/DECISIONS.md | Capture the choice of variant B for cart/plan alignment. | docs | no |
| create | backend/apps/market/api/__init__.py | Expose the new API submodules for cart and plan submissions. | backend | no |
| create | backend/apps/market/api/cart.py | Implement the `/v1/market/cart/` sugar endpoint handling add/update/remove flows. | backend | no |
| create | backend/apps/market/api/plan.py | Implement the `/v1/market/plan/` sugar endpoint orchestrating meal plan items. | backend | no |
| modify | backend/apps/market/urls.py | Register the new cart/plan submission endpoints alongside existing routes. | backend | no |
| create | backend/apps/market/tests/test_cart_plan_endpoints.py | Cover happy-path mutations and validation for the sugar endpoints. | backend | no |
| modify | frontend/src/types/market.ts | Define payload/response types for cart and plan submissions. | frontend | no |
| modify | frontend/src/api/market.ts | Delegate cart/plan mutations to feature-level clients. | frontend | no |
| modify | frontend/src/features/market/cards/ProductCard.tsx | Call the new cart submission API and sync the Zustand store. | frontend | no |
| modify | frontend/src/features/market/cards/RecipeCard.tsx | Call the plan submission API and align success handling. | frontend | no |
| create | frontend/src/features/market/cart/api.ts | Provide a scoped HTTP client for cart submissions. | frontend | no |
| create | frontend/src/features/market/cart/form.ts | Define the cart submission form schema and helpers. | frontend | no |
| create | frontend/src/features/market/plan/api.ts | Provide a scoped HTTP client for plan submissions. | frontend | no |
| create | frontend/src/features/market/plan/form.ts | Define the plan submission form schema and helpers. | frontend | no |
| create | frontend/src/tests/marketCartPlan.test.ts | Assert API payload normalization and validation failures. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the cart/plan endpoint integration milestone. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the cart/plan submission diff entry. | docs | no |

## 2025-11-08 – commit TBD (market stack baseline audit)

Summary: Captured baseline gaps between marketplace implementations and issue templates, logged missing request-id propagation
in logs, and recorded follow-up decisions for cart/plan endpoint alignment.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | docs/codex/DIFF.codex.md | Record the audit findings and logging observations for traceability. | docs | no |
| create | docs/codex/adr/2025-11-08-cart-plan-endpoints.md | Draft ADR covering cart/plan endpoint alignment options pending implementation. | docs | no |

## 2025-11-08 – commit TBD (market page-number pagination adoption)

Summary: Switch the market listings to page/page_size parameters across the backend and frontend, provide typed client helpers,
and cover the new response contract with unit tests.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | backend/apps/market/pagination.py | Return page metadata alongside count/next/previous so API consumers can drive page-number pagination. | backend | no |
| create | backend/apps/market/tests/test_pagination.py | Assert that the store listing endpoint yields page and page_size values when paginating. | backend | no |
| modify | frontend/src/api/market.ts | Request market collections with page/page_size params and extract the next page number from response links. | frontend | no |
| modify | frontend/src/types/market.ts | Model the shared market paginated response with page and page_size fields. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Drive infinite scroll with numeric page params instead of cursor tokens. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.test.tsx | Align mocks with the updated market collection response shape. | frontend | no |
| create | frontend/src/tests/marketApi.test.ts | Cover the market API client pagination params and next-page extraction logic. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the market pagination contract update for traceability. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the market pagination adoption changes in the diff journal. | docs | no |

## 2025-11-07 – commit TBD (market search sidebar placement)

Summary: Embed the marketplace search control inside the desktop filter sidebar on laptop and monitor breakpoints so the layout
matches the filter block design.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Render the search control inside the desktop filter sidebar while keeping the mobile/tablet placement intact. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.tsx | Accept an optional search control slot and surface the shared heading inside the sidebar card. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the search placement adjustment for traceability. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the desktop search relocation in the diff journal. | docs | no |

## 2025-11-06 – commit TBD (market filters sheet overlay release)

Summary: Allow the Radix sheet portal to unmount while closed so mobile and tablet navigation lands on content instead of a locked filter overlay, and capture the regression with a focused test harness.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/ui/Sheet.tsx | Stop force-mounting the dialog overlay/content so the body scroll lock clears when the sheet is closed while preserving motion transitions. | frontend | no |
| create | frontend/src/pages/market/MarketCollectionPage.test.tsx | Reproduce the mobile navigation flow and assert the filters sheet stays closed on initial render. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the overlay release fix and regression guard for traceability. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the overlay release adjustments in the diff journal. | docs | no |

## 2025-11-05 – commit TBD (market filters sheet gating)

Summary: Ensure marketplace sections load their content first on mobile and tablet by resetting the filter sheet state when switching categories or breakpoints.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Close the mobile filters sheet when entering a new section or widening to desktop so navigation no longer lands inside the overlay. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Record the filter sheet gating adjustment for traceability. | docs | no |

## 2025-11-04 – commit TBD (market filters toolbar removal)

Summary: Retire the duplicated top-of-page market filters so the redesigned sidebar and sheet experiences remain the single source of truth across breakpoints.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Drop the legacy toolbar instance, keep the mobile sheet for sub-desktop layouts, and expose the sidebar filters on all wide screens. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.tsx | Delete the unused toolbar variant and streamline shared sort/range controls for the sidebar and sheet. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.test.tsx | Point the unit test at the sidebar component to reflect the surviving interaction contract. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.stories.tsx | Showcase the sidebar and sheet pair in Storybook instead of the removed toolbar. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the UI cleanup for traceability. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the toolbar removal diff entry. | docs | no |


## 2025-11-03 – commit TBD (market search test enablement)

Summary: Restore backend installability and search coverage by making gcld3 optional and switching the market search API tests to JWT-aware API clients compatible with the DRF settings.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | backend/requirements.txt | Drop the hard gcld3 dependency so local/CI environments without protobuf headers can install backend requirements. | backend | no |
| modify | backend/apps/market/tests/test_search_api.py | Authenticate with DRF APIClient and adjust fixtures/query data so the search endpoint test passes under SQLite/JWT defaults. | backend | no |
| modify | docs/codex/CHANGELOG.codex.md | Log the market search test enablement for traceability. | docs | no |

## 2025-11-02 – commit TBD (market search filters implementation)

Summary: Deliver the premium `/market` search overlay and responsive filters with a unified backend search service, richer facet filtering, and redesigned tablet-to-desktop layouts.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | backend/apps/market/constants.py | Centralize quick filter definitions shared by the search service and API responses. | backend | no |
| create | backend/apps/market/services/__init__.py | Define the services package for marketplace utilities. | backend | no |
| create | backend/apps/market/services/search.py | Implement aggregated search logic with facets, suggestions, and resource-specific mapping. | backend | no |
| create | backend/apps/market/migrations/0002_product_metadata.py | Add a JSON `metadata` field to products for search facets and badges. | backend | yes – run `python manage.py migrate apps.market 0002` |
| modify | backend/apps/market/models.py | Extend `Product` with metadata storage used for quick filters and availability checks. | backend | covered by migration |
| modify | backend/apps/market/serializers.py | Expose product metadata and wire serializers for the new search payload. | backend | no |
| modify | backend/apps/market/urls.py | Register the `/v1/market/search/` endpoint. | backend | no |
| modify | backend/apps/market/views.py | Add `MarketSearchView` and expand list filters for stores, products, and recipes. | backend | no |
| modify | backend/seeds/market.py | Seed product and store metadata to exercise new filters. | backend | no |
| create | backend/apps/market/tests/__init__.py | Initialize the marketplace test package. | backend | no |
| create | backend/apps/market/tests/test_search_api.py | Cover search aggregation, resource scoping, and quick filter responses. | backend | no |
| modify | frontend/src/api/market.ts | Add the `searchMarket` client helper and request typing. | frontend | no |
| create | frontend/src/features/market/components/MarketSearch.tsx | Build the popover + overlay search UI with quick filters and previews. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.tsx | Restructure filters into toolbar, sidebar, and mobile sheet variants. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.test.tsx | Update tests for the new toolbar component contract. | frontend | no |
| modify | frontend/src/features/market/components/MarketFilters.stories.tsx | Point Storybook to the toolbar variant for interactive demos. | frontend | no |
| modify | frontend/src/pages/market/MarketCollectionPage.tsx | Integrate the command search, responsive filters, and desktop sidebar. | frontend | no |
| modify | frontend/src/types/market.ts | Define search result and quick filter typings consumed by the UI. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Record the end-to-end market search implementation milestone. | docs | no |

## 2025-11-01 – commit TBD (market premium filters search spec)

Summary: Capture the premium tablet-to-desktop filters and command search experience for /market so design and engineering share a single blueprint anchored to the existing UI kit.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| create | docs/frontend/market/market-filters-search-premium.md | Document layouts, interactions, accessibility, and data contracts for the refreshed /market filters and command search. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Log the premium filters/search specification for traceability. | docs | no |

## 2025-10-31 – commit TBD (market layout spacing)

Summary: Restore horizontal breathing room for the market shell so its border no longer collides with the dashboard rail on wide layouts or mobile safe areas.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/pages/market/MarketLayout.tsx | Remove negative horizontal margins and enforce full-width layout so the market shell keeps consistent spacing from the dashboard rail and viewport edges. | frontend | no |
| modify | docs/codex/DIFF.codex.md | Document the market layout spacing adjustment for traceability. | docs | no |

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
