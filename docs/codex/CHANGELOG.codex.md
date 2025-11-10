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
