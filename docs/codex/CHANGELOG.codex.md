# Codex Changelog

## 2025-11-13

- Added a dedicated Stage 6 `/market` sorting & filtering prompt plus RCA for the ordering crash so future backend/frontend iterations share consistent context. See DIFF entry “2025-11-13 – commit TBD (market ordering stage6 prompt & RCA docs)”.

## 2025-11-12

- Enabled marketplace ordering + rating/protein/price filters end-to-end, added JSONB metadata indexes, synced SPA filter config, and expanded backend/frontend coverage. See DIFF entry “2025-11-12 – commit TBD (market filters ordering + rating support)”.

## 2025-11-11

- Flattened marketplace serializers/viewsets to expose enriched store/product/recipe metadata, refreshed SPA typings and cards to avoid NaN placeholders, and added regression tests across backend and frontend. See DIFF entry “2025-11-11 – commit TBD (market card flat fields)”.

## 2025-11-10

- Added the `/api/v1/market/events/` SSE proxy with JWT authentication, frontend hook rename, contract docs, and a local load sanity check. See DIFF entry “2025-11-10 – commit TBD (market events SSE proxy)”.

## 2025-11-09

- Added sugar endpoints for `/v1/market/cart/` and `/v1/market/plan/`, aligned the SPA forms/stores, and covered the new contract with backend/frontend tests. See DIFF entry “2025-11-09 – commit TBD (market cart/plan submission endpoints)”.

## 2025-11-08

- Adopted page-number pagination for market listings across backend and frontend layers and covered the contract with unit
  tests. See DIFF entry “2025-11-08 – commit TBD (market page-number pagination adoption)”.

## 2025-11-07

- Moved the marketplace desktop search into the filter sidebar so laptop and monitor layouts align with the filter block design. See DIFF entry “2025-11-07 – commit TBD (market search sidebar placement)”.

## 2025-11-06

- Released the market filters sheet overlay when closed so mobile/tablet navigation no longer lands on a locked dialog and added a regression test to guard the behavior. See DIFF entry “2025-11-06 – commit TBD (market filters sheet overlay release)”.

## 2025-11-05

- Stopped the market mobile/tablet navigation from opening directly inside the filters sheet by resetting the overlay when switching sections or breakpoints. See DIFF entry “2025-11-05 – commit TBD (market filters sheet gating)”.

## 2025-11-04

- Removed the duplicated market toolbar filters so only the sidebar/sheet experiences remain visible across breakpoints. See DIFF entry “2025-11-04 – commit TBD (market filters toolbar removal)”.


## 2025-11-03

- Unblocked backend market search testing by dropping the hard gcld3 dependency and authenticating the DRF search tests via API client fixtures. See DIFF entry “2025-11-03 – commit TBD (market search test enablement)”.

## 2025-11-02

- Implemented the `/market` premium search and responsive filter experience end-to-end across backend APIs and the React tablet/desktop UI. See DIFF entry “2025-11-02 – commit TBD (market search filters implementation)”.

## 2025-11-01

- Published the premium `/market` tablet-to-desktop filters and command search specification aligned with the UI kit. See DIFF entry “2025-11-01 – commit TBD (market premium filters search spec)”.

## 2025-10-30

- Migrated the billing wallet actions to the shared UI kit button component to restore theming and hover states on both light and dark themes. See DIFF entry “2025-10-30 – commit TBD (billing buttons ui kit)”.

## 2025-10-29

- Scoped the grid shimmer canvas palette so the dark theme no longer shifts its neon colors. See DIFF entry “2025-10-29 – commit TBD (grid shimmer dark override)”.

## 2025-10-28

- Refined the sticky navigation bar for scroll-aware reveal/hide behavior and neutralized control accents. See DIFF entry “2025-10-28 – commit TBD”.

## 2025-10-27

- Harmonized the frontend palette with the new UI kit tokens across shared styles and interactive components. See DIFF entry “2025-10-27 – commit d9ebc28”.
- Stabilized the sheet component animation keys and refreshed global form controls to rely solely on the new UI kit tokens. See DIFF entry “2025-10-27 – commit HEAD”.
