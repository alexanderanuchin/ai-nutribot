# Premium /market Filters & Search Specification (Tablet–Desktop)

## 1. Intent & Scope
- **Audience:** React 19+ web client using the existing UI kit tokens and interaction patterns.
- **Scope:** Tablet (≥768px), Laptop (≈1280px), and Desktop Wide (≥1440px) viewports for `/market` and all sub-tabs.
- **Out of scope:** Mobile layouts (≤767px) and any color, shadow, or typography additions outside of current design tokens.
- **Tone:** Light, refined, and premium — achieved with micro-typography steps, airy spacing, and soft shadows (levels 100–200 from UI kit).

## 2. Shared Design Principles
1. **Hierarchy through micro-steps:** Heading/label typography uses `font-size` steps of ±2 from base token; filter chips use `label-sm`, secondary metadata `caption-xs`.
2. **Airy grid:** Base spacing derived from `space-8` increments with `space-4` micro-adjustments for dense clusters (chips).
3. **Delicate separation:** Use `border-subtle` token (1px) and `shadow-elev-100` default. Hover lifts to `shadow-elev-150`; focus ring uses `focus-ring-primary`.
4. **Glassmorphism restraint:** Popovers/overlays use `surface-glass-80` background with `backdrop-blur-sm` only when area ≥ 320px; no stacked blurs.
5. **Motion:** Entrance/exit transitions 150–180 ms ease-out. Popovers: fade + translateY(8–12px). Filter rearrange uses 200 ms cubic-bezier with inertia.
6. **Sticky without heft:** Sticky bars rely on background token `surface-base` + `shadow-elev-80` (single layer). Avoid double shadows.

## 3. Layouts by Breakpoint
### Tablet (768–1024px)
- **Filter bar:** Single row, horizontally scrollable chips + inline quantifiers. Overflow control reveals `…` button (opens `FiltersOverflowSheet`). Sticky beneath global nav.
- **Search entry:** Centered icon button (`SearchTriggerIconButton`) next to tabs. Activates popover anchored to nav.
- **Popover width:** 520px max or `calc(100vw - 96px)`.
- **Extended mode:** Fullscreen overlay (`CommandOverlay`) sliding from top, covering content with dimmed background `surface-scrim-60`.

### Laptop (~1280px)
- **Filter panel:** Two-row structure inside `FiltersToolbar`.
  - Row 1: Primary chips (diet, delivery, category), quick quantifiers.
  - Row 2: Secondary filters (`MoreFiltersGroup`), saved sets dropdown, `ResetAll` button.
- **Search entry:** Compact field (`SearchTriggerField`) right-aligned within toolbar or left of section tabs depending on layout constraints; width 240px.
- **Extended mode:** Half-width dock panel (`CommandDock`) sliding from right (max 720px). Content pushes underlying layout 16px with `safe-area` padding.

### Desktop Wide (≥1440px / 1600+)
- **Top bar:** Fixed `MarketHeader` with search trigger left of user actions.
- **Side column:** `FiltersSidebar` (320px) collapsible. Contains structured facets with section headings.
- **Search:** Command palette invoked via Ctrl/⌘ K or `/`. Default view: centered 720px popover; extended overlay expands to 1200px width with results grid on left (max 2 columns) and preview panel right (400px).
- **Behavior:** Filters bar remains sticky at top with subtle shadow; sidebar scrolls independently with `position: sticky; top: header height + 16px`.

## 4. Search Experience
### 4.1 Entry Points
- `SearchTriggerIconButton`: icon-only on tablet; displays placeholder text on larger breakpoints.
- Keyboard shortcuts: global key listener (client-side only) opens `CommandPalette`.

### 4.2 Popover Content
- **Input field:** `CommandSearchInput` with debounced (250 ms) onChange; shows inline skeleton placeholder while awaiting suggestions.
- **Sections:**
  - `Recent Searches` (up to 5, persisted in IndexedDB via `useSearchCache`).
  - `Popular Now` (server-driven, `GET /market/search/popular`).
  - `Last Applied Filters` (chip list with remove).
  - `Quick Filters` reflecting active tab; e.g., Recipes → `≤ 30 мин`, `Без глютена`.
- **Interactions:** Arrow keys navigate suggestions; `Tab` cycles sections; `Shift+Tab` reverse. `Enter` commits selection.

### 4.3 Extended Mode Overlay (`CommandExplorer`)
- **Layout:**
  - Left column: `SearchResultList` (virtualized, up to 3k items) grouped by content type (Recipes, Products, etc.).
  - Right column: `ResultPreviewPane` with imagery, macros, actions (Add to plan, View store, Replace ingredient).
  - Top bar: breadcrumbs of applied filters + `Save Search` CTA.
- **Tabs:** Secondary segmentation by `/market` categories; default mirrors current tab with options to jump.
- **Quick actions:** `CommandActionsGrid` at bottom-left for operations (Add to list, Build meal plan, Hide ingredient).
- **Saved searches:** `SavedSearchesCarousel` (horizontal) surfaces pinned queries.
- **State handling:**
  - Loading: skeleton rows (title + meta placeholders) via `SkeletonStack`.
  - No results: panel with icon, text `«Не нашли результатов. Снимите фильтр «{X}» или расширьте радиус доставки.»` + action button.
  - Error: inline alert with `Retry` button and short message.
- **Transitions:** overlay fades in 180 ms; `ResultPreviewPane` crossfades when selection changes (150 ms).

### 4.4 Data & Performance
- React 19 suspense boundaries around `SearchSuggestions` and `SearchResultList` with streaming fallback.
- Debounced queries with optimistic insertion of chips (Undo snack bar 3s).
- Cache suggestions per tab via `useSearchCache` hook using TanStack Query with background revalidation.
- Extended mode lazy-loaded via `React.lazy` + suspense to avoid initial bundle bloat.
- Virtualized list (e.g., `react-virtuoso`) with dynamic row height support.

### 4.5 Accessibility
- `aria-controls`, `aria-expanded` on trigger; popover labelled by internal heading.
- `role="combobox"` for input with `aria-autocomplete="list"`.
- `Esc` closes layers; `Ctrl+Enter` applies filters without closing overlay.
- Focus trap ensures keyboard loops within overlay until dismissed.

## 5. Filters System Architecture
### 5.1 Core Components (Conceptual)
- `FiltersToolbar`
  - **Props:** `primaryFacets: FacetConfig[]`, `secondaryFacets: FacetConfig[]`, `activeSet: FilterSet`, `onApply(filters)`, `onReset()`, `onReorder(primaryOrder)`.
  - **Behavior:** Renders chips, handles drag-drop reorder, shows `ResetAll` button with applied count.
- `FilterChip`
  - **Props:** `facetId`, `label`, `active`, `badgeCount`, `onToggle()`, `onOpenDetails()`.
  - **States:** default, hover (shadow lift), focus (focus ring), active (filled surface), disabled.
- `FacetPopover`
  - **Props:** `facet: FacetConfig`, `value`, `onChange`, `metricsId`.
  - Renders sliders, checklists, or tag inputs depending on type.
- `FilterSidebar`
  - **Props:** `facets`, `collapsed`, `onToggleCollapsed`, `onFacetChange`.
  - Sticky container on Desktop Wide.
- `SavedFilterSetsSwitcher`
  - **Props:** `sets: FilterSetSummary[]`, `activeId`, `onSelect(id)`, `onManage()`.
- `FiltersOverflowSheet` (Tablet only)
  - **Props:** `hiddenFacets`, `onApply`, `onDismiss`.

### 5.2 FacetConfig Schema (conceptual TypeScript)
```ts
interface FacetConfig {
  id: string;
  label: string;
  type: 'toggle' | 'multi-select' | 'range' | 'stepper' | 'chips' | 'searchable-list';
  icon?: ReactNode;
  description?: string;
  tokens?: {
    surface?: string; // e.g., 'surface-elev-low'
    accent?: string;  // for active state highlight
  };
  dataSource: 'static' | 'api';
  apiEndpoint?: string;
  dependsOn?: string[]; // facet ids this facet listens to
  presets?: PresetOption[];
  unit?: string; // kcal, ₽, мин
  localizationKey: string; // for i18n strings
}
```

### 5.3 Apply Flow
1. User toggles facets → optimistic `onApplyPending` updates chip badges and button label `Показать {count}`.
2. Sticky Apply button (if unsaved changes) uses inline loader token `loader-inline-sm` while fetching.
3. Undo toast (`Toast` component) appears bottom-right (desktop) or bottom-center (tablet), 4-second timeout.

## 6. Facet Catalogue by Tab
| Tab | Facet | Type | Data Source | Dependencies |
| --- | --- | --- | --- | --- |
| Рецепты | Время готовки | range (slider + presets ≤15/30/45) | static presets + API suggestions | — |
|  | Сложность | chips (3 levels) | static | — |
|  | Кухня | multi-select searchable | `/market/recipes/cuisines` | Locale |
|  | Калории/порция | range | static presets + API | Диеты |
|  | Диеты | multi-select chips | `/market/diets` | — |
|  | Аллергены (исключить) | multi-select negative chips | `/market/allergens` | — |
|  | Ингредиенты включить | searchable-list with autocomplete | `/market/ingredients` | — |
|  | Ингредиенты исключить | searchable-list negative | `/market/ingredients` | `Ингредиенты включить` (mutual suggestions) |
|  | Техника | multi-select icons | static | — |
|  | Оценка | range (star) | static | — |
|  | Сезонность | toggle chips | `/market/seasons` | — |
| Готовые блюда и рационы | Калории/день | range | static presets | — |
|  | Цель | chips | `/market/goals` | — |
|  | План (длительность) | stepper (days/weeks) | static | — |
|  | Доставка (время/окно) | multi-select schedule | `/market/delivery-windows` | Город |
|  | Диеты и аллергены | combined multi-select | `/market/diets`, `/market/allergens` | — |
|  | Цена/день | range | `/market/pricing` | Валюта |
|  | Пробный сет | toggle | static | — |
| Продукты | Категория/подкатегория | hierarchical tree | `/market/catalog/tree` | — |
|  | Цена | range + presets | `/market/pricing` | Валюта |
|  | Бренд | searchable list | `/market/brands` | Категория |
|  | Эко/органик/сертификаты | multi-select | `/market/certifications` | — |
|  | Срок годности | range (days) | `/market/shelf-life` | — |
|  | Рейтинг | range | static | — |
|  | Наличие/склад | toggle group | `/market/inventory` | Город |
|  | Акции | toggle | `/market/promotions` | — |
| Полезные товары | Назначение | chips | `/market/wellness/uses` | — |
|  | Материал | multi-select | `/market/materials` | — |
|  | Экологичность/сертификаты | multi-select | `/market/certifications` | — |
|  | Совместимость | searchable list | `/market/compatibility` | Категория |
|  | Гарантия | range (months) | static | — |
|  | Цена | range | `/market/pricing` | Валюта |
|  | Рейтинг | range | static | — |
| Магазины | Радиус/город | range (km) + select | `/market/geography/cities` | User location |
|  | Открыто сейчас | toggle | static (computed) | Время |
|  | Доставка/самовывоз | toggle | static | — |
|  | Минимальный заказ | range | `/market/pricing` | Валюта |
|  | Рейтинг | range | static | — |
|  | Промо | toggle | `/market/promotions` | — |
| Партнёры доставки | Покрытие/районы | multi-select map list | `/market/logistics/zones` | User location |
|  | SLA и окна | chips (≤30 мин, 30–60, 2ч+) | `/market/logistics/sla` | — |
|  | Стоимость/бесплатный порог | range | `/market/logistics/pricing` | Валюта |
|  | Рейтинг | range | static | — |
|  | Экодоставка | toggle | static | — |

## 7. Interaction State Map
| Element | Hover | Focus | Active | Disabled |
| --- | --- | --- | --- | --- |
| Filter chip | Shadow → `elev-150`, background `surface-alt`. | `focus-ring-primary` (1.5px), maintain hover tone. | Background `surface-accent-10`, text `text-primary`. | Opacity 40%, cursor default. |
| Apply button | Shadow `elev-120`, icon tint lighten. | Focus ring + subtle scale 1.01. | Fills `action-primary-solid`. | Reduced opacity; retains outline. |
| Reset | Text underline fade-in 120 ms. | Focus ring, background `surface-subtle`. | Text color `text-primary`. | Hidden when no filters. |
| Command input | Border `border-strong`. | Focus ring + caret accent. | — | — |
| Result row | Background `surface-alt`, left indicator bar. | Outline none (listbox handles). | Highlight `surface-accent-05`. | — |
| Sidebar facet heading | Underline appears. | Focus ring around block. | Collapsible toggles arrow. | — |

## 8. Keyboard Navigation Map
1. `Ctrl/⌘ K` / `/` → open popover (focus input).
2. `Tab` through sections: Input → Recent → Popular → Quick Filters → Footer actions.
3. `ArrowDown/Up` inside a section cycles items; `Home/End` jump to first/last.
4. `Ctrl+→`/`Ctrl+←` jump between `/market` content tabs.
5. `Enter` selects; `Shift+Enter` open preview on Desktop wide while keeping list focus.
6. `Esc` closes current layer; double `Esc` closes overlay + returns focus to trigger.
7. Filter chips: `Tab` enters toolbar, `Arrow keys` navigate horizontal order, `Space` toggles, `Enter` opens `FacetPopover`.
8. Reordering: `Ctrl+Shift+Arrow` moves chip left/right; announces via ARIA live region.

## 9. Localization & Content Rules
- Use `i18n.t` keys `market.search.placeholder`, `market.filters.reset`, etc.
- Range units adapt (`мин`, `kcal`, `₽`) using locale-specific formatters.
- Pluralization handled via ICU strings e.g. `market.results.count` with Russian cases (1/2-4/others) and English singular/plural.

## 10. Content States Copy
- **Empty results:** `Не нашли результатов. Снимите «{facet}» или расширьте радиус доставки.` / `No matches. Try clearing “{facet}” or widening delivery radius.`
- **Zero saved filters:** `Пока нет сохранённых наборов. Настройте фильтры и нажмите «Сохранить».`
- **Error:** `Что-то пошло не так. Попробуйте ещё раз.` / `Something went wrong. Retry?`
- **Skeleton labels:** `Загружаем подборку…` / `Loading curated picks…`
- **Apply button loading:** Replace text with spinner + `Применяем…` / `Applying…`

## 11. Token Usage Mini-Guide
- **Spacing:** base `space-8` for chip gaps, `space-12` between toolbar rows, `space-24` between sidebar sections.
- **Radii:** chips `radius-lg`, popovers `radius-xl`, overlay corners `radius-xxl` (desktop only).
- **Typography:**
  - Toolbar labels: `font-label-sm`
  - Popover headings: `font-title-xs`
  - Metadata: `font-caption-xs`
- **Shadows:** default `shadow-elev-100`, hover `shadow-elev-150`, overlay `shadow-elev-200`.
- **Colors:** backgrounds use `surface-base`, active chips `surface-accent-10`, text `text-primary`, muted `text-tertiary`.
- **Blur:** apply `backdrop-blur-xs` only on overlays >50% opacity; avoid stacking with additional filters.

## 12. Engineering Considerations
- **React 19:**
  - Server Components for static filter taxonomies (e.g., diets) streamed into toolbar; hydrate interactive chips client-side.
  - Suspense for search suggestions; streaming fallback ensures fast first paint.
- **Data fetching:** TanStack Query with `staleTime` tuned per facet (e.g., certifications daily, promotions 5 min).
- **Undo model:** apply filters optimistically; if server rejects, show toast `Не удалось применить. Отменили изменения.`.
- **Caching:** search suggestions stored per tab key in local cache; persisted per profile.
- **Performance:** avoid nested overlays; limit to single scrim + one popover. Ensure virtualization for result lists and preview prefetch.
- **Accessibility testing:** integrate `@testing-library/user-event` flows for keyboard map; run axe on popover/overlay states.

## 13. Metrics & Instrumentation
- Track events:
  - `search.command.open` (source: trigger/hotkey).
  - `search.command.extend` (extended mode opened).
  - `filters.apply` (payload: facet ids, result count).
  - `filters.undo`.
  - `search.result.preview` (type, time to click).
  - `filters.set.save` / `filters.set.load`.
- Connect to product analytics (e.g., PostHog) via `useAnalytics` hook; include `rid` extra metadata in logs.
- Heatmap instrumentation: track facet interactions by tab for insights.

## 14. Deliverables Checklist
- Annotated Figma frames for Tablet, Laptop, Desktop Wide per tab.
- State matrix covering hover/focus/active/disabled/loading/error.
- Keyboard navigation diagram referencing section 8 sequence.
- Facet data table (section 6) exported to product wiki.
- Content strings packaged for localization (section 10).
- Token usage cheat sheet (section 11) shared with design/dev teams.
