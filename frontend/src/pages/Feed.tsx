import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { useSearchParams } from 'react-router-dom'

import { fetchFeed } from '../api/feed'
import FeedTabs from '../features/feed/components/FeedTabs'
import NewsCard from '../features/feed/components/NewsCard'
import RecipeCard from '../features/feed/components/RecipeCard'
import DealCard from '../features/feed/components/DealCard'
import FeedSkeleton from '../features/feed/components/FeedSkeleton'
import { useFeedRealtime } from '../features/feed/hooks/useFeedRealtime'
import { FEED_TABS } from '../features/feed/constants'
import type { FeedRealtimeEvent, FeedTab } from '../types/feed'
import SearchBox from '../components/nav/SearchBox'
import { useAuth } from '../hooks/useAuth'

const DEFAULT_SCROLL: Record<FeedTab, number> = {
  news: 0,
  recipes: 0,
  deals: 0,
}

const ZERO_COUNTS: Record<FeedTab, number> = {
  news: 0,
  recipes: 0,
  deals: 0,
}

const EMPTY_FILTERS: Record<FeedTab, Record<string, string | boolean>> = {
  news: {},
  recipes: {},
  deals: {},
}

const FILTER_PRESETS = {
  recipes: [
    {
      key: 'free',
      label: 'Бесплатные',
      isActive: (filters: Record<string, string | boolean>) => filters.price_max === '0',
      apply: (active: boolean) => ({ price_max: active ? '0' : undefined, price_min: undefined }),
    },
    {
      key: 'premium',
      label: 'Платные',
      isActive: (filters: Record<string, string | boolean>) => filters.price_min === '1',
      apply: (active: boolean) => ({ price_min: active ? '1' : undefined, price_max: undefined }),
    },
    {
      key: 'fast',
      label: 'До 30 мин',
      isActive: (filters: Record<string, string | boolean>) => filters.cook_time_max === '30',
      apply: (active: boolean) => ({ cook_time_max: active ? '30' : undefined }),
    },
  ],
  deals: [
    {
      key: 'online',
      label: 'Онлайн',
      isActive: (filters: Record<string, string | boolean>) => filters.is_online === '1',
      apply: (active: boolean) => ({ is_online: active ? '1' : undefined }),
    },
  ],
} as const

function sanitizeFilters(filters: Record<string, string | boolean | undefined>): Record<string, string | boolean> {
  const result: Record<string, string | boolean> = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    if (typeof value === 'string' && value.trim() === '') return
    result[key] = value
  })
  return result
}

function areFiltersEqual(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

function FilterChip({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'rounded-full px-3 py-1.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
        active ? 'bg-primary text-primary-foreground' : 'bg-muted/50 text-muted-foreground hover:bg-muted'
      )}
    >
      {children}
    </button>
  )
}

export default function Feed() {
  const queryClient = useQueryClient()
  const { profile } = useAuth()
  const userCity = profile?.city?.trim() ?? ''
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTabParam = (searchParams.get('tab') as FeedTab | null) ?? 'news'
  const [activeTab, setActiveTab] = useState<FeedTab>(FEED_TABS.some(tab => tab.id === initialTabParam) ? initialTabParam : 'news')
  const [tabFilters, setTabFilters] = useState<Record<FeedTab, Record<string, string | boolean>>>(EMPTY_FILTERS)
  const [newsSearch, setNewsSearch] = useState('')
  const [pendingCounts, setPendingCounts] = useState<Record<FeedTab, number>>(ZERO_COUNTS)
  const [scrollPositions, setScrollPositions] = useState<Record<FeedTab, number>>(DEFAULT_SCROLL)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const activeFilters = tabFilters[activeTab] || {}
  const filterKey = useMemo(() => JSON.stringify(activeFilters), [activeFilters])

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, refetch } = useInfiniteQuery({
    queryKey: ['feed', activeTab, filterKey],
    queryFn: ({ pageParam }) => fetchFeed({ type: activeTab, cursor: pageParam ?? null, filters: activeFilters }),
    getNextPageParam: lastPage => lastPage.nextCursor,
    staleTime: 5_000,
    refetchOnWindowFocus: false,
  })

  const pages = data?.pages ?? []
  const items = useMemo(() => pages.flatMap(page => page.items), [pages])

  const handleRealtime = useCallback((event: FeedRealtimeEvent) => {
    setPendingCounts(prev => ({ ...prev, [event.tab]: (prev[event.tab] ?? 0) + 1 }))
  }, [])

  useFeedRealtime({ feed: activeTab, onEvent: handleRealtime })

  useEffect(() => {
    if (activeTab === 'news') {
      setNewsSearch(String(tabFilters.news?.search ?? ''))
    }
  }, [activeTab, tabFilters.news])

  useEffect(() => {
    if (activeTab !== 'news') return
    const timer = window.setTimeout(() => {
      setTabFilters(prev => {
        const sanitized = sanitizeFilters({ ...prev.news, search: newsSearch || undefined })
        if (areFiltersEqual(prev.news, sanitized)) return prev
        return { ...prev, news: sanitized }
      })
    }, 350)
    return () => window.clearTimeout(timer)
  }, [activeTab, newsSearch])

  const updateFilters = useCallback((tab: FeedTab, updater: (filters: Record<string, string | boolean>) => Record<string, string | boolean | undefined>) => {
    let changed = false
    setTabFilters(prev => {
      const nextRaw = updater(prev[tab] ?? {})
      const next = sanitizeFilters(nextRaw)
      if (areFiltersEqual(prev[tab] ?? {}, next)) {
        return prev
      }
      changed = true
      return { ...prev, [tab]: next }
    })
    if (changed) {
      setPendingCounts(prev => ({ ...prev, [tab]: 0 }))
    }
  }, [])

  const handleChangeTab = useCallback((tab: FeedTab) => {
    if (tab === activeTab) return
    if (typeof window !== 'undefined') {
      setScrollPositions(prev => ({ ...prev, [activeTab]: window.scrollY }))
    }
    setActiveTab(tab)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tab', tab)
      return next
    }, { replace: true })
  }, [activeTab, setSearchParams])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const nextPosition = scrollPositions[activeTab] ?? 0
    window.scrollTo({ top: nextPosition, behavior: 'auto' })
  }, [activeTab, scrollPositions])

  useEffect(() => {
    const node = sentinelRef.current
    if (!node || !hasNextPage) return
    const observer = new IntersectionObserver(entries => {
      const entry = entries[0]
      if (entry?.isIntersecting && !isFetchingNextPage) {
        fetchNextPage()
      }
    }, { root: null, threshold: 0.5 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, items.length])

  const handleApplyUpdates = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['feed', activeTab] })
    setPendingCounts(prev => ({ ...prev, [activeTab]: 0 }))
  }, [activeTab, queryClient])

  const handleManualRefresh = useCallback(() => {
    void refetch()
    setPendingCounts(prev => ({ ...prev, [activeTab]: 0 }))
  }, [activeTab, refetch])

  const renderItem = useCallback((item: any) => {
    if (activeTab === 'news') {
      return <NewsCard key={`news-${item.id}`} item={item} />
    }
    if (activeTab === 'recipes') {
      return <RecipeCard key={`recipe-${item.id}`} item={item} />
    }
    return <DealCard key={`deal-${item.id}`} item={item} />
  }, [activeTab])

  const badgeCounts = pendingCounts

  return (
    <section className="flex min-h-full flex-col gap-6">
      <div className="flex flex-col gap-4">
        <FeedTabs active={activeTab} onChange={handleChangeTab} badges={badgeCounts} />
        {activeTab === 'news' ? (
          <SearchBox value={newsSearch} onChange={setNewsSearch} placeholder="Поиск новостей" />
        ) : null}
        {activeTab === 'recipes' ? (
          <div className="flex flex-wrap gap-2">
            {FILTER_PRESETS.recipes.map(preset => {
              const currentFilters = tabFilters.recipes ?? {}
              const active = preset.isActive(currentFilters)
              return (
                <FilterChip
                  key={preset.key}
                  active={active}
                  onClick={() =>
                    updateFilters('recipes', current => ({ ...current, ...preset.apply(!active) }))
                  }
                >
                  {preset.label}
                </FilterChip>
              )
            })}
            <FilterChip
              active={tabFilters.recipes?.sort === 'popular'}
              onClick={() =>
                updateFilters('recipes', current => ({
                  ...current,
                  sort: current.sort === 'popular' ? undefined : 'popular',
                }))
              }
            >
              Популярные
            </FilterChip>
            <FilterChip
              active={tabFilters.recipes?.sort === 'rating'}
              onClick={() =>
                updateFilters('recipes', current => ({
                  ...current,
                  sort: current.sort === 'rating' ? undefined : 'rating',
                }))
              }
            >
              Высокий рейтинг
            </FilterChip>
          </div>
        ) : null}
        {activeTab === 'deals' ? (
          <div className="flex flex-wrap gap-2">
            {FILTER_PRESETS.deals.map(preset => {
              const currentFilters = tabFilters.deals ?? {}
              const active = preset.isActive(currentFilters)
              return (
                <FilterChip
                  key={preset.key}
                  active={active}
                  onClick={() =>
                    updateFilters('deals', current => ({ ...current, ...preset.apply(!active) }))
                  }
                >
                  {preset.label}
                </FilterChip>
              )
            })}
            {userCity ? (
              <FilterChip
                active={tabFilters.deals?.city === userCity}
                onClick={() =>
                  updateFilters('deals', current => ({
                    ...current,
                    city: current.city === userCity ? undefined : userCity,
                  }))
                }
              >
                Только мой город
              </FilterChip>
            ) : null}
            <FilterChip
              active={tabFilters.deals?.sort === 'discount'}
              onClick={() =>
                updateFilters('deals', current => ({
                  ...current,
                  sort: current.sort === 'discount' ? undefined : 'discount',
                }))
              }
            >
              По скидке
            </FilterChip>
          </div>
        ) : null}
      </div>

      {pendingCounts[activeTab] > 0 ? (
        <button
          type="button"
          onClick={handleApplyUpdates}
          className="flex items-center justify-center gap-2 rounded-2xl bg-primary/15 px-4 py-2 text-sm font-semibold text-primary transition hover:bg-primary/20"
        >
          Новых публикаций: {pendingCounts[activeTab]} — нажми, чтобы обновить
        </button>
      ) : null}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Лента</h2>
        <button
          type="button"
          onClick={handleManualRefresh}
          className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground transition hover:border-primary/60 hover:text-foreground"
        >
          Обновить
        </button>
      </div>

      <div className="flex flex-col gap-4">
        {isLoading && items.length === 0
          ? Array.from({ length: 3 }).map((_, index) => <FeedSkeleton key={index} variant={activeTab} />)
          : null}
        {items.length > 0 ? items.map(renderItem) : null}
        {!isLoading && items.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-border/60 bg-muted/20 p-6 text-center text-sm text-muted-foreground">
            Пока нет публикаций. Попробуйте изменить фильтры или загляните позже.
          </div>
        ) : null}
        <div ref={sentinelRef} aria-hidden="true" />
        {isFetchingNextPage ? <FeedSkeleton variant={activeTab} /> : null}
      </div>
    </section>
  )
}