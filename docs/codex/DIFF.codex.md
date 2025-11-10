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
