import { useCallback, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { RefreshCwIcon, ShoppingCartIcon, SparklesIcon, UtensilsCrossedIcon } from 'lucide-react'
import clsx from 'clsx'

import { fetchMarketCollection, type MarketCollectionItemMap, type MarketResource } from '../../api/market'
import { useMarketRealtime } from '../../features/market/hooks/useMarketRealtime'
import MarketListSkeleton from '../../features/market/components/MarketListSkeleton'
import {
  MARKET_PRICE_LIMITS,
  MARKET_SORT_OPTIONS,
  MarketFiltersSidebar,
  MarketFiltersMobileSheet,
} from '../../features/market/components/MarketFilters'
import MarketSearch, { MarketSearchHandle } from '../../features/market/components/MarketSearch'
import MarketPageHeader from '../../features/market/components/MarketPageHeader'
import RecipeCard from '../../features/market/cards/RecipeCard'
import ProductCard from '../../features/market/cards/ProductCard'
import StoreCard from '../../features/market/cards/StoreCard'
import {
  MARKET_FILTERS,
  MARKET_RESOURCE_DESCRIPTION,
  MARKET_RESOURCE_LABELS,
  MARKET_RESOURCE_TITLE,
} from '../../features/market/constants'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { useMarketCartStore, selectCartTotals } from '../../features/market/stores/cartStore'
import { useMarketPlanStore, selectPlanTotals } from '../../features/market/stores/planStore'
import { useSafeArea } from '../../hooks/useSafeArea'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  SearchInput,
} from '../../components/ui'
import type { MarketQuickFilter } from '../../types/market'

interface MarketCollectionPageProps<T extends MarketResource> {
  resource: T
}

type MarketCardComponent<T extends MarketResource> = ComponentType<{ item: MarketCollectionItemMap[T] }>

const BANNER_AUTO_HIDE_MS = 12000

const SORT_PARAM_MAP: Record<MarketResource, Record<string, string | undefined>> = {
  recipes: {
    relevance: undefined,
    time_asc: 'time_minutes',
    calories_asc: 'calories',
  },
  products: {
    recommended: undefined,
    price_asc: 'price',
    price_desc: '-price',
    discount: '-discount',
  },
  stores: {
    top_rated: '-rating',
    eta_asc: 'eta',
    fresh: '-freshness',
  },
}

const AVAILABILITY_MAP: Record<MarketResource, string> = {
  recipes: 'available',
  products: 'available',
  stores: 'open',
}

interface FreshBannerProps {
  visible: boolean
  count: number
  resource: MarketResource
  refreshing: boolean
  onRefresh: () => void
  onDismiss: () => void
}

function FreshBanner({ visible, count, resource, refreshing, onRefresh, onDismiss }: FreshBannerProps) {
  const shouldReduceMotion = useReducedMotion()
  return (
    <AnimatePresence>
      {visible && count > 0 ? (
        <motion.div
          key="fresh-banner"
          drag="y"
          dragConstraints={{ top: 0, bottom: shouldReduceMotion ? 0 : 48 }}
          dragElastic={0.22}
          onDragEnd={(_, info) => {
            if (info.offset.y > 40 || info.velocity.y > 180) {
              onDismiss()
            }
          }}
          initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -16 }}
          animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, transition: { type: 'spring', damping: 24, stiffness: 240 } }}
          exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -12, transition: { duration: 0.16 } }}
          className="sticky top-3 z-30 flex items-center justify-between gap-3 rounded-2xl border border-primary/45 bg-primary/15 px-5 py-3 text-sm text-primary shadow-level-2 backdrop-blur"
        >
          <div className="flex flex-col gap-1">
            <span className="font-semibold">Свежие поступления: +{count}</span>
            <span className="text-xs text-primary/80">
              Обновите список, чтобы увидеть новые {MARKET_RESOURCE_LABELS[resource]}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="primary" loading={refreshing} onClick={onRefresh} leadingIcon={<RefreshCwIcon className="h-4 w-4" aria-hidden="true" />}>
              Обновить
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onDismiss}
              leadingIcon={<SparklesIcon className="h-4 w-4" aria-hidden="true" />}
            >
              Скрыть
            </Button>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}

function FloatingSummary({
  cart,
  plan,
}: {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
}) {
  const priceFormatter = useMemo(() =>
    cart.currency
      ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: cart.currency, maximumFractionDigits: 0 })
      : null,
  [cart.currency])
  return (
    <div className="hidden xl:block xl:sticky xl:top-28">
      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-4" elevation={2}>
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Корзина</span>
              <span className="text-title font-semibold text-foreground">{cart.quantity} позиций</span>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <ShoppingCartIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : 'Добавьте продукты из каталога'}
          </p>
          <Button variant="primary" size="md" href="/market/products">
            Оформить
          </Button>
        </Card>
        <Card className="flex flex-col gap-4" elevation={2}>
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">План питания</span>
              <span className="text-title font-semibold text-foreground">{plan.count} рецептов</span>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <UtensilsCrossedIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {plan.servings > 0
              ? `${plan.servings} порций · ${plan.calories.toLocaleString('ru-RU')} ккал`
              : 'Добавьте блюда в индивидуальный план'}
          </p>
          <Button variant="secondary" size="md" href="/market/recipes">
            Собрать меню
          </Button>
        </Card>
      </div>
    </div>
  )
}

function MobileSummaryBar({
  cart,
  plan,
  onFilters,
  onSearch,
}: {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
  onFilters: () => void
  onSearch: () => void
}) {
  const safeArea = useSafeArea()
  const priceFormatter = cart.currency
    ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: cart.currency, maximumFractionDigits: 0 })
    : null
  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-2 border-t border-border/70 bg-card/95 px-4 py-3 shadow-level-3 backdrop-blur lg:hidden"
      style={{ paddingBottom: `calc(${safeArea.bottom}px + 0.75rem)` }}
    >
      <Button variant="ghost" size="sm" className="min-w-[90px]" onClick={onFilters}>
        Фильтры
      </Button>
      <div className="flex flex-1 flex-col gap-1">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Корзина · {cart.quantity}</span>
          <span>{cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : '0 ₽'}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>План · {plan.count}</span>
          <span>{plan.servings > 0 ? `${plan.servings} порций` : 'Пусто'}</span>
        </div>
      </div>
      <Button variant="primary" size="sm" onClick={onSearch}>
        Поиск
      </Button>
    </div>
  )
}

export function MarketCollectionPage<T extends MarketResource>({ resource }: MarketCollectionPageProps<T>) {
  const filterDefinitions = MARKET_FILTERS[resource] ?? []
  const [chipFilters, setChipFilters] = useState<Record<string, boolean>>({})
  const [priceRange, setPriceRange] = useState<[number, number]>(MARKET_PRICE_LIMITS[resource])
  const [ratingValue, setRatingValue] = useState(0)
  const [availability, setAvailability] = useState<'all' | 'available'>('all')
  const [sortValue, setSortValue] = useState(() => MARKET_SORT_OPTIONS[resource][0]?.value ?? 'relevance')
  const [searchValue, setSearchValue] = useState('')
  const debouncedSearch = useDebouncedValue(searchValue, 350)
  const [bannerState, setBannerState] = useState({ count: 0, visible: false })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const hideBannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const searchHandleRef = useRef<MarketSearchHandle | null>(null)
  const isTabletUp = useMediaQuery('(min-width: 768px)')
  const isDesktopWide = useMediaQuery('(min-width: 1440px)')

  const cartTotals = useMarketCartStore(
    selectCartTotals,
    (a, b) => a.count === b.count && a.quantity === b.quantity && a.amount === b.amount && a.currency === b.currency,
  )
  const planTotals = useMarketPlanStore(
    selectPlanTotals,
    (a, b) => a.count === b.count && a.servings === b.servings && a.calories === b.calories,
  )

  useEffect(() => {
    setChipFilters({})
    setPriceRange(MARKET_PRICE_LIMITS[resource])
    setRatingValue(0)
    setAvailability('all')
    setSortValue(MARKET_SORT_OPTIONS[resource][0]?.value ?? 'relevance')
    setSearchValue('')
    setBannerState({ count: 0, visible: false })
    setFiltersOpen(false)
    if (hideBannerTimerRef.current) {
      clearTimeout(hideBannerTimerRef.current)
      hideBannerTimerRef.current = null
    }
  }, [resource])

  useEffect(() => {
    if (filtersOpen && isDesktopWide) {
      setFiltersOpen(false)
    }
  }, [filtersOpen, isDesktopWide])

  const filterParams = useMemo(() => {
    const params: Record<string, string | number | boolean> = {}
    filterDefinitions.forEach(definition => {
      if (!chipFilters[definition.id]) return
      const existing = params[definition.param]
      if (existing == null) {
        params[definition.param] = definition.value
        return
      }
      params[definition.param] = `${String(existing)},${String(definition.value)}`
    })
    const [minPrice, maxPrice] = MARKET_PRICE_LIMITS[resource]
    if (priceRange[0] > minPrice) {
      params.min_price = priceRange[0]
    }
    if (priceRange[1] < maxPrice) {
      params.max_price = priceRange[1]
    }
    if (ratingValue > 0) {
      params.min_rating = ratingValue
    }
    if (availability === 'available') {
      params[AVAILABILITY_MAP[resource]] = true
    }
    const ordering = SORT_PARAM_MAP[resource][sortValue]
    if (ordering) {
      params.ordering = ordering
    }
    return params
  }, [availability, chipFilters, filterDefinitions, priceRange, ratingValue, resource, sortValue])

  const filtersKey = useMemo(
    () =>
      JSON.stringify({
        params: filterParams,
        sortValue,
        priceRange,
        ratingValue,
        availability,
      }),
    [availability, filterParams, priceRange, ratingValue, sortValue],
  )

  const queryKey = useMemo(
    () => ['market', resource, filtersKey, debouncedSearch.trim()] as const,
    [resource, filtersKey, debouncedSearch],
  )

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isFetching,
    isFetchingNextPage,
    isError,
    refetch,
  } = useInfiniteQuery({
    queryKey,
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }) => {
      const { items, nextCursor, raw } = await fetchMarketCollection({
        resource,
        cursor: pageParam,
        filters: filterParams,
        search: debouncedSearch.trim() || undefined,
        pageSize: resource === 'stores' ? 10 : 12,
      })
      return { items, nextCursor, raw }
    },
    getNextPageParam: lastPage => lastPage.nextCursor,
  })

  const isRefreshing = isFetching && !isLoading && !isFetchingNextPage

  const items = useMemo(
    () => (data?.pages ? data.pages.flatMap(page => page.items) : []),
    [data?.pages],
  )

  const totalAvailable = data?.pages?.[0]?.raw?.count ?? null

  const CardComponent = useMemo<MarketCardComponent<T>>(() => {
    switch (resource) {
      case 'recipes':
        return RecipeCard as MarketCardComponent<T>
      case 'products':
        return ProductCard as MarketCardComponent<T>
      default:
        return StoreCard as MarketCardComponent<T>
    }
  }, [resource])

  const skeletonVariant = resource === 'stores' ? 'stores' : resource === 'products' ? 'products' : 'recipes'

  const handleToggleFilter = useCallback((id: string, active: boolean) => {
    setChipFilters(state => ({ ...state, [id]: active }))
  }, [])

  const handleResetFilters = useCallback(() => {
    setChipFilters({})
    setPriceRange(MARKET_PRICE_LIMITS[resource])
    setRatingValue(0)
    setAvailability('all')
    setSortValue(MARKET_SORT_OPTIONS[resource][0]?.value ?? 'relevance')
  }, [resource])

  const handleQuickFilterSelect = useCallback(
    (filter: MarketQuickFilter) => {
      if (filter.resource !== resource) return
      const target = filterDefinitions.find(definition => definition.id === filter.id)
      if (!target) return
      setChipFilters(state => ({ ...state, [target.id]: true }))
    },
    [filterDefinitions, resource],
  )

  useMarketRealtime({
    resource,
    onEvent: event => {
      const delta = event.payload.fresh_count && event.payload.fresh_count > 0 ? event.payload.fresh_count : 1
      setBannerState(prev => ({ count: prev.count + delta, visible: true }))
      if (hideBannerTimerRef.current) {
        clearTimeout(hideBannerTimerRef.current)
      }
      hideBannerTimerRef.current = setTimeout(() => {
        setBannerState({ count: 0, visible: false })
        hideBannerTimerRef.current = null
      }, BANNER_AUTO_HIDE_MS)
    },
  })

  useEffect(
    () => () => {
      if (hideBannerTimerRef.current) {
        clearTimeout(hideBannerTimerRef.current)
        hideBannerTimerRef.current = null
      }
    },
    [],
  )

  useEffect(() => {
    const node = sentinelRef.current
    if (!node) return undefined
    const observer = new IntersectionObserver(
      entries => {
        const [entry] = entries
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage()
        }
      },
      { root: null, rootMargin: '320px', threshold: 0.1 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, resource])

  const handleRefreshBanner = useCallback(async () => {
    await refetch({ throwOnError: false })
    if (hideBannerTimerRef.current) {
      clearTimeout(hideBannerTimerRef.current)
      hideBannerTimerRef.current = null
    }
    setBannerState({ count: 0, visible: false })
  }, [refetch])

  const filterComponentProps = useMemo(
    () => ({
      resource,
      filters: filterDefinitions,
      chipValue: chipFilters,
      onToggleChip: handleToggleFilter,
      onReset: handleResetFilters,
      sortValue,
      onSortChange: setSortValue,
      priceRange,
      onPriceRangeChange: setPriceRange,
      ratingValue,
      onRatingChange: setRatingValue,
      availability,
      onAvailabilityChange: setAvailability,
    }),
    [
      resource,
      filterDefinitions,
      chipFilters,
      handleToggleFilter,
      handleResetFilters,
      sortValue,
      priceRange,
      ratingValue,
      availability,
    ],
  )

  const searchControl = isTabletUp ? (
    <MarketSearch
      ref={searchHandleRef}
      resource={resource}
      value={searchValue}
      onSubmit={setSearchValue}
      onQuickFilterSelect={handleQuickFilterSelect}
    />
  ) : (
    <SearchInput
      ref={searchInputRef}
      value={searchValue}
      onChange={event => setSearchValue(event.target.value)}
      placeholder="Поиск по названию, ингредиентам или тегам"
      onClear={() => setSearchValue('')}
      className="max-w-full"
    />
  )

  const listContent = useMemo(() => {
    if (resource === 'stores') {
      return (
        <div className="flex flex-col gap-4">
          {items.map(store => (
            <CardComponent key={store.id} item={store} />
          ))}
        </div>
      )
    }
    return (
      <div className={clsx('grid gap-4', resource === 'products' ? 'sm:grid-cols-2 xl:grid-cols-3' : 'sm:grid-cols-2 xl:grid-cols-3')}>
        {items.map(item => (
          <CardComponent key={item.id} item={item} />
        ))}
      </div>
    )
  }, [CardComponent, items, resource])

  const showEmptyState = !isLoading && !isError && items.length === 0

  return (
    <div className="flex flex-col gap-6 pb-28 lg:pb-16">
      <div
        className={clsx(
          'flex flex-col gap-4',
          isDesktopWide ? 'xl:sticky xl:top-20 xl:z-30 xl:bg-background/95 xl:backdrop-blur xl:pt-3 xl:pb-4 xl:shadow-level-2/20' : '',
        )}
      >
        <MarketPageHeader
          title={MARKET_RESOURCE_TITLE[resource]}
          description={MARKET_RESOURCE_DESCRIPTION[resource]}
          action={
            totalAvailable ? (
              <Badge tone="primary">{totalAvailable.toLocaleString('ru-RU')} {MARKET_RESOURCE_LABELS[resource]}</Badge>
            ) : null
          }
        >
          <div className={clsx('flex flex-col gap-3', isTabletUp ? 'lg:flex-row lg:items-center lg:justify-between' : '')}>
            {searchControl}
          </div>
        </MarketPageHeader>
        {!isDesktopWide ? (
          <MarketFiltersMobileSheet
            {...filterComponentProps}
            open={filtersOpen}
            onOpenChange={setFiltersOpen}
          />
        ) : null}
      </div>

      <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:gap-8">
        <div className="flex flex-col gap-6">
          <FreshBanner
            visible={bannerState.visible}
            count={bannerState.count}
            resource={resource}
            refreshing={isRefreshing}
            onRefresh={handleRefreshBanner}
            onDismiss={() => {
              if (hideBannerTimerRef.current) {
                clearTimeout(hideBannerTimerRef.current)
                hideBannerTimerRef.current = null
              }
              setBannerState({ count: 0, visible: false })
            }}
          />

          {isLoading ? (
            <MarketListSkeleton variant={skeletonVariant} />
          ) : isError ? (
            <Card elevation={2} className="border-destructive/40 bg-destructive/10 text-destructive">
              Не удалось загрузить {MARKET_RESOURCE_LABELS[resource]}. Попробуйте обновить страницу.
            </Card>
          ) : showEmptyState ? (
            <EmptyState
              title="Пока пусто"
              description="Измените фильтры или загляните позже — мы уже подбираем новые предложения."
              icon={<SparklesIcon className="h-6 w-6" aria-hidden="true" />}
            />
          ) : (
            <>{listContent}</>
          )}

          <AnimatePresence>{isFetchingNextPage ? <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><MarketListSkeleton variant={skeletonVariant} count={resource === 'stores' ? 2 : 3} /></motion.div> : null}</AnimatePresence>

          <div ref={sentinelRef} aria-hidden="true" className="h-px w-full" />
        </div>
        <aside className="hidden xl:block xl:sticky xl:top-28">
          <div className="flex flex-col gap-6">
            <MarketFiltersSidebar {...filterComponentProps} />
            <FloatingSummary cart={cartTotals} plan={planTotals} />
          </div>
        </aside>
      </div>

      <MobileSummaryBar
        cart={cartTotals}
        plan={planTotals}
        onFilters={() => setFiltersOpen(true)}
        onSearch={() => {
          if (isTabletUp) {
            searchHandleRef.current?.openExtended()
            return
          }
          searchInputRef.current?.focus()
          window.scrollTo({ top: 0, behavior: 'smooth' })
        }}
      />
    </div>
  )
}

export default MarketCollectionPage
export { FreshBanner }