import { forwardRef, useMemo, useState } from 'react'
import { FilterIcon, SparklesIcon } from 'lucide-react'
import clsx from 'clsx'

import type { MarketResource } from '../../../types/market'
import type { MarketFilterDefinition } from '../constants'
import {
  Badge,
  Button,
  Chip,
  RangeSlider,
  SegmentedControl,
  SheetClose,
  SheetContent,
  SheetRoot,
  SheetTrigger,
  ToggleGroupItem,
  ToggleGroupRoot,
} from '../../../components/ui'

export const MARKET_SORT_OPTIONS: Record<MarketResource, Array<{ value: string; label: string }>> = {
  recipes: [
    { value: 'relevance', label: 'Актуальные' },
    { value: 'time_asc', label: 'По времени' },
    { value: 'calories_asc', label: 'Ккал' },
  ],
  products: [
    { value: 'recommended', label: 'Реком.' },
    { value: 'price_asc', label: 'Цена ↑' },
    { value: 'price_desc', label: 'Цена ↓' },
    { value: 'discount', label: 'Скидки' },
  ],
  stores: [
    { value: 'top_rated', label: 'Лучшие' },
    { value: 'eta_asc', label: 'Доставка' },
    { value: 'fresh', label: 'Новые' },
  ],
}

export const MARKET_PRICE_LIMITS: Record<MarketResource, [number, number]> = {
  recipes: [0, 1200],
  products: [0, 5000],
  stores: [0, 1000],
}

export interface MarketFiltersProps {
  resource: MarketResource
  filters: MarketFilterDefinition[]
  chipValue: Record<string, boolean>
  onToggleChip: (id: string, active: boolean) => void
  onReset: () => void
  sortValue: string
  onSortChange: (value: string) => void
  priceRange: [number, number]
  onPriceRangeChange: (range: [number, number]) => void
  ratingValue: number
  onRatingChange: (value: number) => void
  availability: 'all' | 'available'
  onAvailabilityChange: (value: 'all' | 'available') => void
}

const RATING_CHOICES = [0, 3, 4, 4.5]

function FilterChips({ resource, filters, chipValue, onToggleChip }: Pick<MarketFiltersProps, 'resource' | 'filters' | 'chipValue' | 'onToggleChip'>) {
  return (
    <div className="flex min-h-[44px] items-center gap-2 overflow-x-auto pb-1 pl-1 pr-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
      {filters.map(filter => {
        const selected = Boolean(chipValue[filter.id])
        return (
          <Chip
            key={`${resource}-${filter.id}`}
            selected={selected}
            onClick={() => onToggleChip(filter.id, !selected)}
            tone={selected ? 'primary' : 'muted'}
          >
            {filter.label}
          </Chip>
        )
      })}
    </div>
  )
}

function FilterControls({
  resource,
  sortValue,
  onSortChange,
  priceRange,
  onPriceRangeChange,
  ratingValue,
  onRatingChange,
  availability,
  onAvailabilityChange,
  layout,
}: MarketFiltersProps & { layout: 'tablet' | 'laptop' | 'desktop' }) {
  const sortOptions = MARKET_SORT_OPTIONS[resource]
  const [minPrice, maxPrice] = MARKET_PRICE_LIMITS[resource]
  const priceFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        maximumFractionDigits: 0,
      }),
    [],
  )

  return (
    <div
      className={clsx(
        'grid gap-3 rounded-3xl border border-border/60 bg-card/70 p-3 shadow-level-1 backdrop-blur',
        layout === 'tablet'
          ? 'md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:items-start'
          : 'lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_auto] lg:items-center',
      )}
    >
      <SegmentedControl
        value={sortValue}
        onValueChange={value => value && onSortChange(value)}
        options={sortOptions}
      />
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          <span>Диапазон</span>
          <span>
            {priceFormatter.format(priceRange[0])} — {priceFormatter.format(priceRange[1])}
          </span>
        </div>
        <RangeSlider
          value={priceRange}
          onValueChange={onPriceRangeChange}
          min={minPrice}
          max={maxPrice}
          step={50}
        />
      </div>
      <div
        className={clsx(
          'flex gap-3',
          layout === 'tablet' ? 'flex-col md:flex-row md:items-center' : 'flex-col xl:flex-row xl:items-center',
        )}
      >
        <ToggleGroupRoot
          type="single"
          value={ratingValue.toString()}
          onValueChange={value => onRatingChange(Number(value) || 0)}
          className="inline-flex flex-wrap gap-1 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
          aria-label="Минимальный рейтинг"
        >
          {RATING_CHOICES.map(choice => (
            <ToggleGroupItem key={choice} value={choice.toString()}>
              {choice > 0 ? `${choice}+` : 'Все рейтинги'}
            </ToggleGroupItem>
          ))}
        </ToggleGroupRoot>
        <ToggleGroupRoot
          type="single"
          value={availability}
          onValueChange={value => value && onAvailabilityChange(value as 'all' | 'available')}
          className="inline-flex flex-wrap gap-1 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
          aria-label="Доступность"
        >
          <ToggleGroupItem value="all">Все</ToggleGroupItem>
          <ToggleGroupItem value="available">В наличии</ToggleGroupItem>
        </ToggleGroupRoot>
      </div>
    </div>
  )
}

export interface MarketFiltersToolbarProps extends MarketFiltersProps {
  layout: 'tablet' | 'laptop' | 'desktop'
}

export function MarketFiltersToolbar(props: MarketFiltersToolbarProps) {
  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-col gap-2 rounded-3xl border border-border/60 bg-card/60 p-3 shadow-level-1 backdrop-blur">
        <div className="flex flex-wrap items-center gap-2">
          <FilterChips {...props} />
          <Button variant="ghost" size="sm" className="ml-auto" onClick={props.onReset}>
            Сбросить
          </Button>
        </div>
      </div>
      <FilterControls {...props} />
    </div>
  )
}

export interface MarketFiltersSidebarProps extends MarketFiltersProps {
  title?: string
}

export const MarketFiltersSidebar = forwardRef<HTMLDivElement, MarketFiltersSidebarProps>(function MarketFiltersSidebar(
  props,
  ref,
) {
  const { resource, filters, chipValue, onToggleChip, onReset } = props
  const sortOptions = MARKET_SORT_OPTIONS[resource]
  const [minPrice, maxPrice] = MARKET_PRICE_LIMITS[resource]
  const priceFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        maximumFractionDigits: 0,
      }),
    [],
  )

  return (
    <div ref={ref} className="flex flex-col gap-6 rounded-3xl border border-border/70 bg-card/80 p-5 shadow-level-2 backdrop-blur">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Быстрые фильтры</span>
        <Button variant="ghost" size="sm" onClick={onReset}>
          Сбросить
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {filters.map(filter => {
          const selected = Boolean(chipValue[filter.id])
          return (
            <Chip
              key={`${resource}-sidebar-${filter.id}`}
              selected={selected}
              onClick={() => onToggleChip(filter.id, !selected)}
              tone={selected ? 'primary' : 'muted'}
            >
              {filter.label}
            </Chip>
          )
        })}
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-foreground">Сортировка</span>
          <SegmentedControl
            value={props.sortValue}
            onValueChange={value => value && props.onSortChange(value)}
            options={sortOptions}
          />
        </div>
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-foreground">Диапазон цены</span>
          <span className="text-xs text-muted-foreground">
            {priceFormatter.format(props.priceRange[0])} — {priceFormatter.format(props.priceRange[1])}
          </span>
          <RangeSlider
            value={props.priceRange}
            onValueChange={props.onPriceRangeChange}
            min={minPrice}
            max={maxPrice}
            step={50}
          />
        </div>
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-foreground">Рейтинг</span>
          <ToggleGroupRoot
            type="single"
            value={props.ratingValue.toString()}
            onValueChange={value => props.onRatingChange(Number(value) || 0)}
            className="inline-flex flex-wrap gap-1 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
          >
            {RATING_CHOICES.map(choice => (
              <ToggleGroupItem key={choice} value={choice.toString()}>
                {choice > 0 ? `${choice}+` : 'Все рейтинги'}
              </ToggleGroupItem>
            ))}
          </ToggleGroupRoot>
        </div>
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-foreground">Доступность</span>
          <ToggleGroupRoot
            type="single"
            value={props.availability}
            onValueChange={value => value && props.onAvailabilityChange(value as 'all' | 'available')}
            className="inline-flex flex-wrap gap-1 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
          >
            <ToggleGroupItem value="all">Все</ToggleGroupItem>
            <ToggleGroupItem value="available">В наличии</ToggleGroupItem>
          </ToggleGroupRoot>
        </div>
      </div>
    </div>
  )
})

MarketFiltersSidebar.displayName = 'MarketFiltersSidebar'

export interface MarketFiltersMobileSheetProps extends MarketFiltersProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export const MarketFiltersMobileSheet = forwardRef<HTMLButtonElement, MarketFiltersMobileSheetProps>(function MarketFiltersMobileSheet(
  props,
  ref,
) {
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = props.open !== undefined
  const open = isControlled ? Boolean(props.open) : internalOpen
  const setOpen = props.onOpenChange ?? setInternalOpen
  const sortOptions = MARKET_SORT_OPTIONS[props.resource]
  const [minPrice, maxPrice] = MARKET_PRICE_LIMITS[props.resource]
  const priceFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        maximumFractionDigits: 0,
      }),
    [],
  )

  const activeCount = useMemo(() => {
    const chips = Object.values(props.chipValue).filter(Boolean).length
    const extras = [
      props.sortValue !== MARKET_SORT_OPTIONS[props.resource][0]?.value,
      props.priceRange[0] !== minPrice || props.priceRange[1] !== maxPrice,
      props.ratingValue > 0,
      props.availability === 'available',
    ].filter(Boolean).length
    return chips + extras
  }, [
    props.availability,
    props.chipValue,
    props.priceRange,
    props.ratingValue,
    props.resource,
    props.sortValue,
    maxPrice,
    minPrice,
  ])

  return (
    <SheetRoot open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button ref={ref} variant="secondary" size="md" className="w-full justify-between">
          <span className="inline-flex items-center gap-2">
            <FilterIcon className="h-4 w-4" aria-hidden="true" />
            Фильтры
          </span>

          {activeCount > 0 ? (
            <Badge tone="primary">+{activeCount}</Badge>
          ) : (
            <SparklesIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          )}
        </Button>
      </SheetTrigger>
      <SheetContent title="Фильтры" description="Соберите подборку под ваши задачи">
        <div className="flex flex-col gap-4">
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-foreground">Сортировка</h3>
            <SegmentedControl value={props.sortValue} onValueChange={value => value && props.onSortChange(value)} options={sortOptions} />
          </section>
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">
              <span>Диапазон</span>
              <span>
                {priceFormatter.format(props.priceRange[0])} — {priceFormatter.format(props.priceRange[1])}
              </span>
            </div>
            <RangeSlider value={props.priceRange} onValueChange={props.onPriceRangeChange} min={minPrice} max={maxPrice} step={50} />
          </section>
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-foreground">Рейтинг</h3>
            <ToggleGroupRoot
              type="single"
              value={props.ratingValue.toString()}
              onValueChange={value => props.onRatingChange(Number(value) || 0)}
              className="inline-flex rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
            >
              {RATING_CHOICES.map(choice => (
                <ToggleGroupItem key={choice} value={choice.toString()}>
                  {choice > 0 ? `${choice}+` : 'Все'}
                </ToggleGroupItem>
              ))}
            </ToggleGroupRoot>
          </section>
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold text-foreground">Доступность</h3>
            <ToggleGroupRoot
              type="single"
              value={props.availability}
              onValueChange={value => value && props.onAvailabilityChange(value as 'all' | 'available')}
              className="inline-flex rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1"
            >
              <ToggleGroupItem value="all">Все</ToggleGroupItem>
              <ToggleGroupItem value="available">В наличии</ToggleGroupItem>
            </ToggleGroupRoot>
          </section>
          {props.filters.length ? (
            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-foreground">Теги</h3>
              <div className="flex flex-wrap gap-2">
                {props.filters.map(filter => {
                  const selected = Boolean(props.chipValue[filter.id])
                  return (
                    <Chip
                      key={filter.id}
                      selected={selected}
                      onClick={() => props.onToggleChip(filter.id, !selected)}
                      tone={selected ? 'primary' : 'muted'}
                    >
                      {filter.label}
                    </Chip>
                  )
                })}
              </div>
            </section>
          ) : null}
        </div>
        <div className="mt-6 flex flex-col gap-3">
          <SheetClose asChild>
            <Button variant="primary" size="lg" onClick={() => setOpen(false)}>
              Применить
            </Button>
          </SheetClose>
          <SheetClose asChild>
            <Button variant="ghost" size="md" onClick={() => {
              props.onReset()
              setOpen(false)
            }}>
              Сбросить
            </Button>
          </SheetClose>
        </div>
      </SheetContent>
    </SheetRoot>
  )
})

MarketFiltersMobileSheet.displayName = 'MarketFiltersMobileSheet'

export default MarketFiltersToolbar
