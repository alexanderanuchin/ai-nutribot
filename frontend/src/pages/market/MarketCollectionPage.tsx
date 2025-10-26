import { useCallback, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { Loader2Icon, RefreshCwIcon, SearchIcon, XIcon } from 'lucide-react'
import clsx from 'clsx'

import { fetchMarketCollection } from '../../api/market'
import type { MarketCollectionItemMap, MarketResource } from '../../api/market'
import { useMarketRealtime } from '../../features/market/hooks/useMarketRealtime'
import MarketListSkeleton from '../../features/market/components/MarketListSkeleton'
import MarketFilters from '../../features/market/components/MarketFilters'
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

interface MarketCollectionPageProps<T extends MarketResource> {
  resource: T
}

type MarketCardComponent<T extends MarketResource> = ComponentType<{ item: MarketCollectionItemMap[T] }>

const BANNER_AUTO_HIDE_MS = 12000

function FreshBanner({
  visible,
  count,
  resource,
  refreshing,
  onRefresh,
  onDismiss,
}: {
  visible: boolean
  count: number
  resource: MarketResource
  refreshing: boolean
  onRefresh: () => void
  onDismiss: () => void
}) {
  if (!visible || count <= 0) return null
  return (
    <div className="sticky top-2 z-20 flex items-center justify-between gap-3 rounded-2xl border border-primary/40 bg-primary/10 px-4 py-3 text-sm text-primary shadow-soft">
      <div className="flex flex-col">
        <span className="font-semibold">Свежие поступления: +{count}</span>
        <span className="text-xs text-primary/80">
          Обновите список, чтобы увидеть новые {MARKET_RESOURCE_LABELS[resource]}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground shadow-soft transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {refreshing ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCwIcon className="h-4 w-4" aria-hidden="true" />}
          Обновить
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-primary/40 text-primary transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Скрыть уведомление о свежих предложениях"
        >
          <XIcon className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}

export function MarketCollectionPage<T extends MarketResource>({ resource }: MarketCollectionPageProps<T>) {
  const filterDefinitions = MARKET_FILTERS[resource] ?? []
  const [filtersState, setFiltersState] = useState<Record<string, boolean>>({})
  const [searchValue, setSearchValue] = useState('')
  const debouncedSearch = useDebouncedValue(searchValue, 350)
  const [freshCount, setFreshCount] = useState(0)
  const [bannerVisible, setBannerVisible] = useState(false)
  const hideBannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setFiltersState({})
    setSearchValue('')
    setFreshCount(0)
    setBannerVisible(false)
  }, [resource])

  const filterParams = useMemo(() => {
    const params: Record<string, string | number | boolean> = {}
    filterDefinitions.forEach(definition => {
      if (!filtersState[definition.id]) return
      const existing = params[definition.param]
      if (existing == null) {
        params[definition.param] = definition.value
        return
      }
      params[definition.param] = `${String(existing)},${String(definition.value)}`
    })
    return params
  }, [filterDefinitions, filtersState])

  const filtersKey = useMemo(() => JSON.stringify(filterParams), [filterParams])

  const queryKey = useMemo(
    () => ['market', resource, filtersKey, debouncedSearch.trim()] as const,
    [resource, filtersKey, debouncedSearch]
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
    [data?.pages]
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
    setFiltersState(state => ({ ...state, [id]: active }))
  }, [])

  const handleResetFilters = useCallback(() => {
    setFiltersState({})
  }, [])

  useMarketRealtime({
    resource,
    onEvent: event => {
      const delta = event.payload.fresh_count && event.payload.fresh_count > 0 ? event.payload.fresh_count : 1
      setFreshCount(prev => prev + delta)
      setBannerVisible(true)
      if (hideBannerTimerRef.current) {
        clearTimeout(hideBannerTimerRef.current)
      }
      hideBannerTimerRef.current = setTimeout(() => {
        setBannerVisible(false)
        setFreshCount(0)
      }, BANNER_AUTO_HIDE_MS)
    },
  })

  useEffect(
    () => () => {
      if (hideBannerTimerRef.current) {
        clearTimeout(hideBannerTimerRef.current)
      }
    },
    []
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
      { root: null, rootMargin: '240px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, queryKey])

  const handleRefreshBanner = useCallback(async () => {
    await refetch({ throwOnError: false })
    setFreshCount(0)
    setBannerVisible(false)
  }, [refetch])

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
    const gridClass = resource === 'products' ? 'sm:grid-cols-2 xl:grid-cols-3' : 'sm:grid-cols-2 xl:grid-cols-3'
    return (
      <div className={clsx('grid gap-4', gridClass)}>
        {items.map(item => (
          <CardComponent key={item.id} item={item} />
        ))}
      </div>
    )
  }, [CardComponent, items, resource])

  const showEmptyState = !isLoading && !isError && items.length === 0

  return (
    <div className="flex flex-col gap-6 pb-8">
      <MarketPageHeader
        title={MARKET_RESOURCE_TITLE[resource]}
        description={MARKET_RESOURCE_DESCRIPTION[resource]}
        action={
          totalAvailable ? (
            <span className="inline-flex items-center rounded-full bg-muted/60 px-3 py-1 text-xs font-semibold text-muted-foreground">
              {totalAvailable.toLocaleString('ru-RU')} {MARKET_RESOURCE_LABELS[resource]}
            </span>
          ) : null
        }
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="relative w-full md:max-w-sm">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              type="search"
              value={searchValue}
              onChange={event => setSearchValue(event.target.value)}
              placeholder="Поиск по названию, ингредиентам или тегам"
              className="h-11 w-full rounded-full border border-border/60 bg-background px-10 text-sm text-foreground shadow-inner transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <MarketFilters filters={filterDefinitions} value={filtersState} onToggle={handleToggleFilter} onReset={handleResetFilters} />
        </div>
      </MarketPageHeader>

      <FreshBanner
        visible={bannerVisible}
        count={freshCount}
        resource={resource}
        refreshing={isRefreshing}
        onRefresh={handleRefreshBanner}
        onDismiss={() => {
          setBannerVisible(false)
          setFreshCount(0)
        }}
      />

      {isLoading ? (
        <MarketListSkeleton variant={skeletonVariant} />
      ) : isError ? (
        <div className="rounded-3xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
          Не удалось загрузить {MARKET_RESOURCE_LABELS[resource]}. Попробуйте обновить страницу.
        </div>
      ) : showEmptyState ? (
        <div className="rounded-3xl border border-border/60 bg-muted/30 px-6 py-12 text-center text-sm text-muted-foreground">
          Предложений пока нет — загляните позже или измените фильтры.
        </div>
      ) : (
        <>{listContent}</>
      )}

      {isFetchingNextPage ? <MarketListSkeleton variant={skeletonVariant} count={resource === 'stores' ? 2 : 3} /> : null}

      <div ref={sentinelRef} aria-hidden="true" />
    </div>
  )
}

export default MarketCollectionPage