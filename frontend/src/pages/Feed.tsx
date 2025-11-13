import type { CSSProperties } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { RefreshCwIcon } from 'lucide-react'
import { useLocation, useSearchParams } from 'react-router-dom'

import { fetchFeed } from '../api/feed'
import FeedTabs from '../features/feed/components/FeedTabs'
import NewsCard from '../features/feed/components/NewsCard'
import RecipeCard from '../features/feed/components/RecipeCard'
import DealCard from '../features/feed/components/DealCard'
import FeedSkeleton from '../features/feed/components/FeedSkeleton'
import { useFeedRealtime } from '../features/feed/hooks/useFeedRealtime'
import { FEED_TABS } from '../features/feed/constants'
import type { FeedRealtimeEvent, FeedTab } from '../types/feed'
import type { MarketRealtimeEvent } from '../types/market'
import SearchBox from '../components/nav/SearchBox'
import { useAuth } from '../hooks/useAuth'
import { useTouchDevice } from '../hooks/useTouchDevice'
import { useMarketEvents } from '../features/market/hooks/useMarketEvents'
import MarketUpdatesPanel, { type MarketUpdateEntry } from '../features/feed/components/MarketUpdatesPanel'
import { supportsVerticalSwipeControl, tg } from '../lib/telegram'

function buildDefaultScroll(): Record<FeedTab, number> {
  return {
    news: 0,
    recipes: 0,
    deals: 0,
  }
}

function buildZeroCounts(): Record<FeedTab, number> {
  return {
    news: 0,
    recipes: 0,
    deals: 0,
  }
}

function buildEmptyFilters(): Record<FeedTab, Record<string, string | boolean>> {
  return {
    news: {},
    recipes: {},
    deals: {},
  }
}

const PULL_THRESHOLD = 64
const MAX_PULL_DISTANCE = 136
const SETTLING_DURATION_MS = 280
const FEEDBACK_DURATION_MS = 2000
const BANNER_AUTO_HIDE_MS = 10_000
const SAFE_AREA_TOP = 'calc(env(safe-area-inset-top, 0px) + 0.75rem)'
const MARKET_UPDATES_LIMIT = 5

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

const NEWS_SEO = {
  title: 'Лента новостей — NutriBot',
  description: 'Свежие новости о питании, исследованиях и ЗОЖ с проверенными источниками и модерацией.',
}

const RECIPES_SEO = {
  title: 'Рецепты и план питания — NutriBot',
  description: 'Подборки рецептов, готовые планы питания и рекомендации от NutriBot для вашего стола.',
}

const DEALS_SEO = {
  title: 'Скидки и акции — NutriBot',
  description: 'Лучшие акции и скидки на продукты рядом с вами — следите за выгодными предложениями каждый день.',
}

const SEO_BY_TAB: Record<FeedTab, typeof NEWS_SEO> = {
  news: NEWS_SEO,
  recipes: RECIPES_SEO,
  deals: DEALS_SEO,
}

function sanitizeFilters(filters: Record<string, string | boolean | undefined>): Record<string, string | boolean> {
  const result: Record<string, string | boolean> = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value == null) return
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
        'inline-flex min-h-[2.75rem] min-w-0 items-center justify-center rounded-full px-3 text-xs font-semibold leading-snug transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
        active ? 'bg-primary text-primary-foreground' : 'bg-muted/50 text-muted-foreground hover:bg-muted'
      )}
    >
      <span className="max-w-full break-words text-center">{children}</span>
    </button>
  )
}

type FeedLocationState = {
  tab?: FeedTab
  scrollY?: number
  filters?: Record<string, string | boolean>
}

export default function Feed() {
  const queryClient = useQueryClient()
  const { profile } = useAuth()
  const userCity = profile?.city?.trim() ?? ''
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const locationState = (location.state as FeedLocationState | null) ?? null
  const tabFromParams = (searchParams.get('tab') as FeedTab | null) ?? 'news'
  const initialTabCandidate = locationState?.tab ?? tabFromParams
  const initialTab = FEED_TABS.some(tab => tab.id === initialTabCandidate) ? initialTabCandidate : 'news'
  const [activeTab, setActiveTab] = useState<FeedTab>(initialTab)
  const [tabFilters, setTabFilters] = useState<Record<FeedTab, Record<string, string | boolean>>>(() => {
    const base = buildEmptyFilters()
    if (locationState?.tab && locationState.filters) {
      base[locationState.tab] = sanitizeFilters(locationState.filters)
    }
    return base
  })
  const [newsSearch, setNewsSearch] = useState('')
  const [pendingCounts, setPendingCounts] = useState<Record<FeedTab, number>>(() => buildZeroCounts())
  const [marketUpdates, setMarketUpdates] = useState<MarketUpdateEntry[]>([])
  const [marketUpdatesHidden, setMarketUpdatesHidden] = useState(false)
  const [scrollPositions, setScrollPositions] = useState<Record<FeedTab, number>>(() => {
    if (locationState?.tab) {
      return { ...buildDefaultScroll(), [locationState.tab]: locationState.scrollY ?? 0 }
    }
    return buildDefaultScroll()
  })
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const isAtTopRef = useRef(true)
  const [isAtTop, setIsAtTop] = useState(true)
  const [isOnline, setIsOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))
  const [pullState, setPullState] = useState<'idle' | 'dragging' | 'armed' | 'refreshing' | 'settling'>('idle')
  const [pullDistance, setPullDistance] = useState(0)
  const [pullProgress, setPullProgress] = useState(0)
  const [pullAnimating, setPullAnimating] = useState(false)
  const [pullFeedback, setPullFeedback] = useState<'none' | 'error' | 'offline'>('none')
  const pointerTrackingRef = useRef(false)
  const pointerIdRef = useRef<number | null>(null)
  const startYRef = useRef(0)
  const pullAnimationFrameRef = useRef<number | null>(null)
  const settleTimerRef = useRef<number | null>(null)
  const feedbackTimerRef = useRef<number | null>(null)
  const prevPullStateRef = useRef<typeof pullState>('idle')
  const bannerAutoHideTimerRef = useRef<number | null>(null)
  const lastBannerCountRef = useRef(0)
  const isComponentMountedRef = useRef(true)
  const [bannerHidden, setBannerHidden] = useState(false)
  const [manualRefreshPending, setManualRefreshPending] = useState(false)
  const autoRefreshRef = useRef(false)
  const isTouchDevice = useTouchDevice()
  const pullToRefreshEnabled = isTouchDevice

  const activeFilters = tabFilters[activeTab] || {}
  const filtersSnapshot = useMemo(() => ({ ...activeFilters }), [activeFilters])
  const filterKey = useMemo(() => JSON.stringify(activeFilters), [activeFilters])
  const queryKey = useMemo(() => ['feed', activeTab, filterKey] as const, [activeTab, filterKey])

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => fetchFeed({ type: activeTab, cursor: pageParam ?? null, filters: activeFilters }),
    getNextPageParam: lastPage => lastPage.nextCursor,
    staleTime: 5_000,
    refetchOnWindowFocus: false,
  })

  const pages = data?.pages ?? []
  const items = useMemo(() => pages.flatMap(page => page.items), [pages])

  // ===== вычисления, используемые в эффектах (объявлены ДО эффектов)
  const badgeCounts = pendingCounts
  const showMarketUpdates = !marketUpdatesHidden && marketUpdates.length > 0
  const activePendingCount = badgeCounts[activeTab] ?? 0
  const indicatorVisible = pullToRefreshEnabled && (pullFeedback !== 'none' || pullState !== 'idle')
  const showProgressBar = pullToRefreshEnabled && (pullState === 'dragging' || pullState === 'armed')
  const progressPercent = Math.min(100, Math.round(pullProgress * 100))
  const indicatorMessage = useMemo(() => {
    const isNewsTab = activeTab === 'news'
    if (pullFeedback === 'offline') return 'Офлайн, повторить при подключении'
    if (pullFeedback === 'error') return 'Ошибка, повторить'
    if (pullState === 'refreshing' || pullState === 'settling') {
      return isNewsTab ? 'Обновляем ленту новостей…' : 'Обновление…'
    }
    if (pullState === 'armed') {
      return isNewsTab ? 'Обновляем ленту новостей' : 'Отпустите, чтобы обновить'
    }
    if (pullState === 'dragging') {
      if (isNewsTab) return `Обновим новости на ${progressPercent}%`
      return `Потяните вниз, чтобы обновить — ${progressPercent}%`
    }
    return isNewsTab ? 'Потяните вниз, чтобы обновить новости' : 'Потяните вниз, чтобы обновить'
  }, [activeTab, progressPercent, pullFeedback, pullState])

  const pullSpacerStyle = useMemo<CSSProperties>(
    () => ({
      height: pullDistance,
      transition: pullAnimating ? 'height 0.28s ease' : 'height 0s linear',
    }),
    [pullAnimating, pullDistance]
  )

  const shouldShowBanner =
    activePendingCount > 0 &&
    !bannerHidden &&
    isOnline &&
    pullState !== 'refreshing' &&
    (pullToRefreshEnabled ? !isAtTop : true)
  const showManualRefreshButton = !pullToRefreshEnabled
  const isManualRefreshInProgress = manualRefreshPending
  const isManualRefreshDisabled = isLoading || manualRefreshPending || !isOnline
  const manualRefreshLabel = !isOnline
    ? 'Нет соединения'
    : isManualRefreshInProgress
    ? 'Обновляем…'
    : 'Обновить ленту'
  // ===== /вычисления

  // --- стили скролл-контейнера: запрещаем «пробой» скролла к WebView
  const scrollContainerStyles = useMemo<CSSProperties>(
    () =>
      pullToRefreshEnabled
        ? {
            overscrollBehaviorY: 'none',
            overscrollBehavior: 'none',
            WebkitOverflowScrolling: 'touch',
            touchAction: 'pan-y',
          }
        : {},
    [pullToRefreshEnabled]
  )

  // На время страницы блокируем вертикальные свайпы Telegram WebApp и «пробой» у body
  useEffect(() => {
    const webApp = tg()
    const canControlSwipes = supportsVerticalSwipeControl(webApp)
    try {
      webApp?.expand?.()
      if (canControlSwipes) {
        webApp?.disableVerticalSwipes?.()
      }
    } catch {}
    let prevBodyOverscroll = ''
    if (typeof document !== 'undefined') {
      prevBodyOverscroll = document.body.style.overscrollBehaviorY
      document.body.style.overscrollBehaviorY = 'none'
    }
    return () => {
      try {
        if (canControlSwipes) {
          webApp?.enableVerticalSwipes?.()
        }
      } catch {}
      if (typeof document !== 'undefined') {
        document.body.style.overscrollBehaviorY = prevBodyOverscroll
      }
    }
  }, [])

  const clearPullAnimation = useCallback(() => {
    if (pullAnimationFrameRef.current) {
      cancelAnimationFrame(pullAnimationFrameRef.current)
      pullAnimationFrameRef.current = null
    }
  }, [])

  const schedulePullMetrics = useCallback(
    (distance: number) => {
      const clamped = Math.max(0, Math.min(distance, MAX_PULL_DISTANCE))
      const progress = Math.min(clamped / PULL_THRESHOLD, 1)
      clearPullAnimation()
      if (typeof window === 'undefined') {
        setPullDistance(clamped)
        setPullProgress(progress)
        return
      }
      pullAnimationFrameRef.current = window.requestAnimationFrame(() => {
        setPullDistance(clamped)
        setPullProgress(progress)
      })
    },
    [clearPullAnimation]
  )

  const clearFeedbackTimer = useCallback(() => {
    if (feedbackTimerRef.current) {
      window.clearTimeout(feedbackTimerRef.current)
      feedbackTimerRef.current = null
    }
  }, [])

  const showFeedback = useCallback(
    (type: 'error' | 'offline') => {
      setPullFeedback(type)
      clearFeedbackTimer()
      feedbackTimerRef.current = window.setTimeout(() => {
        setPullFeedback('none')
        feedbackTimerRef.current = null
      }, FEEDBACK_DURATION_MS)
    },
    [clearFeedbackTimer]
  )

  const triggerHaptic = useCallback((duration: number) => {
    if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') return
    try {
      navigator.vibrate(duration)
    } catch {}
  }, [])

  const refetchCurrentTab = useCallback(
    async (options?: { bust?: boolean }) => {
      const bust = options?.bust ?? false
      try {
        if (bust) {
          await queryClient.invalidateQueries({ queryKey, exact: true, refetchType: 'none' })
        }
        await refetch({ throwOnError: true })
        setPendingCounts(prev => ({ ...prev, [activeTab]: 0 }))
        return { ok: true as const }
      } catch (error) {
        return { ok: false as const, error }
      }
    },
    [activeTab, queryClient, queryKey, refetch]
  )

  const refreshAndScrollToTop = useCallback(
    async (options?: { bust?: boolean }) => {
      const container = scrollContainerRef.current
      if (container) {
        container.scrollTo({ top: 0, behavior: 'smooth' })
      }
      if (bannerAutoHideTimerRef.current) {
        window.clearTimeout(bannerAutoHideTimerRef.current)
        bannerAutoHideTimerRef.current = null
      }
      const result = await refetchCurrentTab({ bust: options?.bust ?? false })
      if (!result.ok) setBannerHidden(false)
      return result
    },
    [refetchCurrentTab, setBannerHidden]
  )

  const releasePointerCapture = useCallback(() => {
    const container = scrollContainerRef.current
    if (container && pointerIdRef.current !== null) {
      try {
        container.releasePointerCapture(pointerIdRef.current)
      } catch {}
    }
    pointerIdRef.current = null
  }, [])

  const settleToIdle = useCallback(() => {
    setPullAnimating(true)
    setPullState('settling')
    schedulePullMetrics(0)
    if (settleTimerRef.current) {
      window.clearTimeout(settleTimerRef.current)
    }
    settleTimerRef.current = window.setTimeout(() => {
      setPullAnimating(false)
      setPullState('idle')
      settleTimerRef.current = null
    }, SETTLING_DURATION_MS)
  }, [schedulePullMetrics])

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!pullToRefreshEnabled) return
      if (!event.isPrimary) return
      if (pullState === 'refreshing') return
      const container = scrollContainerRef.current
      if (!container) return
      if (container.scrollTop > 0) return
      pointerTrackingRef.current = true
      pointerIdRef.current = event.pointerId
      startYRef.current = event.clientY
      setPullAnimating(false)
      if (pullFeedback !== 'none') {
        setPullFeedback('none')
        clearFeedbackTimer()
      }
      try {
        container.setPointerCapture(event.pointerId)
      } catch {}
    },
    [pullToRefreshEnabled, pullState, pullFeedback, clearFeedbackTimer]
  )

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!pullToRefreshEnabled) return
      if (!pointerTrackingRef.current || !event.isPrimary) return
      const container = scrollContainerRef.current
      if (!container) return
      if (pullState === 'refreshing') return
      const delta = event.clientY - startYRef.current
      if (container.scrollTop > 0) {
        pointerTrackingRef.current = false
        releasePointerCapture()
        schedulePullMetrics(0)
        setPullState('idle')
        return
      }
      event.preventDefault()
      setPullAnimating(false)
      if (delta <= 0) {
        if (pullState !== 'dragging') setPullState('dragging')
        schedulePullMetrics(0)
        return
      }
      const nextState = delta >= PULL_THRESHOLD ? 'armed' : 'dragging'
      if (pullState !== nextState) setPullState(nextState)
      schedulePullMetrics(delta)
      container.scrollTop = 0
    },
    [pullToRefreshEnabled, pullState, releasePointerCapture, schedulePullMetrics]
  )

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!pullToRefreshEnabled) return
      if (!event.isPrimary) return
      if (!pointerTrackingRef.current) {
        releasePointerCapture()
        return
      }
      pointerTrackingRef.current = false
      releasePointerCapture()
      if (pullState === 'armed') {
        if (!isOnline) {
          showFeedback('offline')
          settleToIdle()
          return
        }
        setPullAnimating(true)
        setPullState('refreshing')
        schedulePullMetrics(Math.max(pullDistance, PULL_THRESHOLD))
        clearFeedbackTimer()
        setPullFeedback('none')
        void (async () => {
          const result = await refetchCurrentTab({ bust: true })
          if (!result.ok) showFeedback('error')
          settleToIdle()
        })()
        return
      }
      if (pullState !== 'idle') settleToIdle()
    },
    [
      clearFeedbackTimer,
      isOnline,
      pullDistance,
      pullState,
      pullToRefreshEnabled,
      refetchCurrentTab,
      releasePointerCapture,
      schedulePullMetrics,
      settleToIdle,
      showFeedback,
    ]
  )

  const handlePointerCancel = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!pullToRefreshEnabled) return
      if (!event.isPrimary) return
      if (!pointerTrackingRef.current) return
      pointerTrackingRef.current = false
      releasePointerCapture()
      settleToIdle()
    },
    [pullToRefreshEnabled, releasePointerCapture, settleToIdle]
  )

  useEffect(() => {
    const previous = prevPullStateRef.current
    if (pullState === 'armed' && previous !== 'armed') triggerHaptic(15)
    if (previous === 'refreshing' && pullState === 'settling' && pullFeedback === 'none') triggerHaptic(15)
    prevPullStateRef.current = pullState
  }, [pullFeedback, pullState, triggerHaptic])

  const handleRealtime = useCallback(
    (event: FeedRealtimeEvent) => {
      setPendingCounts(prev => ({ ...prev, [event.tab]: (prev[event.tab] ?? 0) + 1 }))
      if (event.tab !== activeTab) return
      if (!isOnline) return
      if (pullState !== 'idle') return
      if (!isAtTopRef.current) return
      if (autoRefreshRef.current) return
      autoRefreshRef.current = true
      void (async () => {
        const result = await refetchCurrentTab({ bust: true })
        if (!result.ok) {
          setPendingCounts(prev => ({ ...prev, [event.tab]: (prev[event.tab] ?? 0) }))
        }
        autoRefreshRef.current = false
      })()
    },
    [activeTab, isOnline, pullState, refetchCurrentTab]
  )

  useFeedRealtime({ feed: activeTab, onEvent: handleRealtime })

  const handleMarketRealtime = useCallback(
    (event: MarketRealtimeEvent) => {
      let entity: { id?: number | string } | undefined
      if (event.resource === 'products') {
        entity = event.payload.product
      } else if (event.resource === 'recipes') {
        entity = event.payload.recipe
      } else {
        entity = event.payload.store
      }
      if (!entity || entity.id == null) {
        return
      }
      const key = `${event.resource}-${entity.id}`
      const occurredAt = event.payload.generated_at ?? new Date().toISOString()
      setMarketUpdates(prev => {
        const nextEntry: MarketUpdateEntry = {
          id: key,
          resource: event.resource,
          action: event.payload.action,
          occurredAt,
          product: event.resource === 'products' ? event.payload.product : undefined,
          recipe: event.resource === 'recipes' ? event.payload.recipe : undefined,
          store: event.resource === 'stores' ? event.payload.store : undefined,
        }
        const withoutCurrent = prev.filter(item => item.id !== key)
        return [nextEntry, ...withoutCurrent].slice(0, MARKET_UPDATES_LIMIT)
      })
      setMarketUpdatesHidden(false)
    },
    [],
  )

  useMarketEvents({
    resources: ['products', 'recipes', 'stores'],
    enabled: Boolean(profile),
    onEvent: handleMarketRealtime,
  })

  const handleClearMarketUpdates = useCallback(() => {
    setMarketUpdates([])
    setMarketUpdatesHidden(true)
  }, [])

  const handleDismissMarketUpdates = useCallback(() => {
    setMarketUpdatesHidden(true)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'news') {
      setNewsSearch(String(tabFilters.news?.search ?? ''))
    }
  }, [activeTab, tabFilters.news])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return
    const updatePosition = () => {
      const atTop = container.scrollTop <= 2
      isAtTopRef.current = atTop
      setIsAtTop(atTop)
    }
    updatePosition()
    container.addEventListener('scroll', updatePosition, { passive: true })
    return () => {
      container.removeEventListener('scroll', updatePosition)
    }
  }, [activeTab])

  useEffect(() => {
    const count = pendingCounts[activeTab] ?? 0
    if (count <= 0) {
      lastBannerCountRef.current = 0
      setBannerHidden(false)
      return
    }
    if (count > lastBannerCountRef.current) setBannerHidden(false)
    lastBannerCountRef.current = count
  }, [activeTab, pendingCounts])

  useEffect(() => {
    if (!shouldShowBanner) {
      if (bannerAutoHideTimerRef.current) {
        window.clearTimeout(bannerAutoHideTimerRef.current)
        bannerAutoHideTimerRef.current = null
      }
      return
    }
    if (bannerAutoHideTimerRef.current) {
      window.clearTimeout(bannerAutoHideTimerRef.current)
      bannerAutoHideTimerRef.current = null
    }
    bannerAutoHideTimerRef.current = window.setTimeout(() => {
      setBannerHidden(true)
      bannerAutoHideTimerRef.current = null
    }, BANNER_AUTO_HIDE_MS)
    return () => {
      if (bannerAutoHideTimerRef.current) {
        window.clearTimeout(bannerAutoHideTimerRef.current)
        bannerAutoHideTimerRef.current = null
      }
    }
  }, [shouldShowBanner, activePendingCount])

  useEffect(() => {
    if (!isOnline) setBannerHidden(true)
  }, [isOnline])

  useEffect(
    () => () => {
      isComponentMountedRef.current = false
      clearPullAnimation()
      if (settleTimerRef.current) {
        window.clearTimeout(settleTimerRef.current)
        settleTimerRef.current = null
      }
      if (feedbackTimerRef.current) {
        window.clearTimeout(feedbackTimerRef.current)
        feedbackTimerRef.current = null
      }
      if (bannerAutoHideTimerRef.current) {
        window.clearTimeout(bannerAutoHideTimerRef.current)
        bannerAutoHideTimerRef.current = null
      }
    },
    [clearPullAnimation]
  )

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const handler = () => {
      void refetchCurrentTab({ bust: true })
    }
    ;(window as any).__debugFeedRefresh = handler
    return () => {
      if ((window as any).__debugFeedRefresh === handler) {
        delete (window as any).__debugFeedRefresh
      }
    }
  }, [refetchCurrentTab])

  useEffect(() => {
    if (typeof document === 'undefined') return
    const meta = SEO_BY_TAB[activeTab]
    document.title = meta.title
    const descriptionTag = document.querySelector('meta[name="description"]')
    if (descriptionTag) descriptionTag.setAttribute('content', meta.description)
    const ogTitleTag = document.querySelector('meta[property="og:title"]')
    if (ogTitleTag) ogTitleTag.setAttribute('content', meta.title)
    const ogDescriptionTag = document.querySelector('meta[property="og:description"]')
    if (ogDescriptionTag) ogDescriptionTag.setAttribute('content', meta.description)
  }, [activeTab])

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
    const container = scrollContainerRef.current
    if (container) {
      setScrollPositions(prev => ({ ...prev, [activeTab]: container.scrollTop }))
    }
    setActiveTab(tab)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('tab', tab)
      return next
    }, { replace: true })
  }, [activeTab, setSearchParams])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return
    const nextPosition = scrollPositions[activeTab] ?? 0
    container.scrollTo({ top: nextPosition, behavior: 'auto' })
  }, [activeTab, scrollPositions])

  useEffect(() => {
    const node = sentinelRef.current
    const container = scrollContainerRef.current
    if (!node || !container || !hasNextPage) return
    const observer = new IntersectionObserver(
      entries => {
        const entry = entries[0]
        if (entry?.isIntersecting && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { root: container, rootMargin: '0px 0px 320px 0px', threshold: 0.01 }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [activeTab, fetchNextPage, hasNextPage, isFetchingNextPage, items.length])

  const getCurrentScrollPosition = useCallback(() => {
    const container = scrollContainerRef.current
    if (container) {
      return container.scrollTop
    }
    return scrollPositions[activeTab] ?? 0
  }, [activeTab, scrollPositions])

  const renderItem = useCallback((item: any) => {
    if (activeTab === 'news')
      return (
        <NewsCard
          key={`news-${item.id}`}
          item={item}
          navigationState={{ tab: 'news', scrollY: getCurrentScrollPosition(), filters: filtersSnapshot }}
        />
      )
    if (activeTab === 'recipes') return <RecipeCard key={`recipe-${item.id}`} item={item} />
    return <DealCard key={`deal-${item.id}`} item={item} />
  }, [activeTab, filtersSnapshot, getCurrentScrollPosition])

  const handleBannerClick = useCallback(() => {
    void refreshAndScrollToTop({ bust: true })
  }, [refreshAndScrollToTop])

  const handleBannerClose = useCallback(() => {
    if (bannerAutoHideTimerRef.current) {
      window.clearTimeout(bannerAutoHideTimerRef.current)
      bannerAutoHideTimerRef.current = null
    }
    setBannerHidden(true)
  }, [])

  const handleManualRefresh = useCallback(() => {
    setManualRefreshPending(prev => {
      if (prev) return prev
      void (async () => {
        try {
          await refreshAndScrollToTop({ bust: true })
        } finally {
          if (isComponentMountedRef.current) {
            setManualRefreshPending(false)
          }
        }
      })()
      return true
    })
  }, [refreshAndScrollToTop])

  const handleRetryFetch = useCallback(() => {
    void refetchCurrentTab({ bust: true })
  }, [refetchCurrentTab])

  return (
    <section className="relative flex h-full min-h-0 w-full flex-1 flex-col">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 z-30 flex justify-center px-4"
        style={{ paddingTop: SAFE_AREA_TOP }}
      >
        {shouldShowBanner ? (
          <div className="pointer-events-auto flex w-full max-w-lg items-center justify-center">
            <div className="flex min-w-0 items-center gap-2 rounded-full bg-primary/95 px-3 py-2 text-sm font-semibold text-primary-foreground shadow-sm shadow-black/25">
              <button
                type="button"
                onClick={handleBannerClick}
                className="flex min-w-0 flex-1 items-center gap-2 rounded-full px-1 py-0.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary focus-visible:ring-offset-primary/40"
                aria-label="Показать свежие новости"
              >
                <span className="inline-flex h-2 w-2 flex-none rounded-full bg-primary-foreground/80" aria-hidden="true" />
                <span className="min-w-0 truncate" aria-live="polite">
                  Свежие новости: +{activePendingCount}
                </span>
              </button>
              <button
                type="button"
                onClick={handleBannerClose}
                className="inline-flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary-foreground/10 text-primary-foreground transition hover:bg-primary-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary focus-visible:ring-offset-primary/40"
                aria-label="Скрыть баннер свежих новостей"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="relative flex min-h-0 flex-1 flex-col">
        <div
          ref={scrollContainerRef}
          className="relative flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden"
          style={scrollContainerStyles}
          onPointerDown={pullToRefreshEnabled ? handlePointerDown : undefined}
          onPointerMove={pullToRefreshEnabled ? handlePointerMove : undefined}
          onPointerUp={pullToRefreshEnabled ? handlePointerUp : undefined}
          onPointerCancel={pullToRefreshEnabled ? handlePointerCancel : undefined}
        >
          <div className="relative flex min-h-full w-full flex-col gap-6 pb-12">
            <div aria-hidden="true" style={pullSpacerStyle} />
            {indicatorVisible ? (
              <div
                className="pointer-events-none absolute inset-x-0 top-0 flex justify-center px-4"
                style={{ paddingTop: SAFE_AREA_TOP }}
              >
                <div className="pointer-events-none flex w-full max-w-sm justify-center">
                  <div
                    role="status"
                    aria-live="polite"
                    className="flex min-w-0 items-center gap-3 rounded-full bg-background/90 px-4 py-2 text-xs font-medium text-muted-foreground shadow-sm shadow-black/15 ring-1 ring-border/40"
                  >
                    {showProgressBar ? (
                      <div className="h-2 w-16 flex-none overflow-hidden rounded-full bg-muted/60" aria-hidden="true">
                        <div
                          className="h-full rounded-full bg-primary transition-[width]"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    ) : (
                      <div className="h-2 w-2 flex-none rounded-full bg-primary/70" aria-hidden="true" />
                    )}
                    <span className="min-w-0 truncate">{indicatorMessage}</span>
                  </div>
                </div>
              </div>
            ) : null}

            {/* было pt-4 — стало pt-2, чтобы «меню от верха» было ближе */}
            <div className="flex w-full flex-col gap-6 px-4">
              <div className="flex w-full flex-col gap-4">
                <FeedTabs active={activeTab} onChange={handleChangeTab} badges={badgeCounts} />
                {showMarketUpdates ? (
                  <MarketUpdatesPanel
                    updates={marketUpdates}
                    onClear={handleClearMarketUpdates}
                    onDismiss={handleDismissMarketUpdates}
                  />
                ) : null}
                {showManualRefreshButton ? (
                  <div className="flex w-full justify-end">
                    <button
                      type="button"
                      onClick={handleManualRefresh}
                      disabled={isManualRefreshDisabled}
                      className="inline-flex items-center gap-2 rounded-full border border-border bg-background/90 px-4 py-2 text-sm font-semibold text-muted-foreground shadow-sm transition hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:bg-background"
                    >
                      <RefreshCwIcon className="h-4 w-4" aria-hidden="true" />
                      <span>{manualRefreshLabel}</span>
                    </button>
                  </div>
                ) : null}
                {activeTab === 'news' ? (
                  <SearchBox value={newsSearch} onChange={setNewsSearch} placeholder="Поиск новостей" />
                ) : null}
                {activeTab === 'news' ? (
                  <div className="flex min-w-0 flex-wrap gap-2">
                    <FilterChip
                      active={tabFilters.news?.tonality === 'positive'}
                      onClick={() =>
                        updateFilters('news', current => ({
                          ...current,
                          tonality: current.tonality === 'positive' ? undefined : 'positive',
                        }))
                      }
                    >
                      Позитивные
                    </FilterChip>
                    <FilterChip
                      active={tabFilters.news?.tonality === 'negative'}
                      onClick={() =>
                        updateFilters('news', current => ({
                          ...current,
                          tonality: current.tonality === 'negative' ? undefined : 'negative',
                        }))
                      }
                    >
                      Негативные
                    </FilterChip>
                    <FilterChip
                      active={tabFilters.news?.clickbait_max === '0.35'}
                      onClick={() =>
                        updateFilters('news', current => ({
                          ...current,
                          clickbait_max: current.clickbait_max === '0.35' ? undefined : '0.35',
                          toxicity_max: current.toxicity_max === '0.4' ? undefined : '0.4',
                        }))
                      }
                    >
                      Без кликбейта
                    </FilterChip>
                    <FilterChip
                      active={tabFilters.news?.is_flagged === '1'}
                      onClick={() =>
                        updateFilters('news', current => ({
                          ...current,
                          is_flagged: current.is_flagged === '1' ? undefined : '1',
                        }))
                      }
                    >
                      Только на проверке
                    </FilterChip>
                    <FilterChip
                      active={tabFilters.news?.is_flagged === 'any'}
                      onClick={() =>
                        updateFilters('news', current => ({
                          ...current,
                          is_flagged: current.is_flagged === 'any' ? undefined : 'any',
                        }))
                      }
                    >
                      Включая проверку
                    </FilterChip>
                  </div>
                ) : null}
                {activeTab === 'recipes' ? (
                  <div className="flex min-w-0 flex-wrap gap-2">
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
                  <div className="flex min-w-0 flex-wrap gap-2">
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

              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="min-w-0 flex-1 text-lg font-semibold text-foreground">Лента</h2>
              </div>

              <div className="flex w-full flex-col gap-4 pb-6">
                {isError ? (
                  <div className="flex flex-col gap-2 rounded-3xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive dark:border-destructive/30 dark:bg-destructive/20">
                    <span>
                      Не удалось загрузить данные.{' '}
                      {error instanceof Error ? error.message : 'Попробуйте обновить страницу.'}
                    </span>
                    <div>
                      <button
                        type="button"
                        onClick={handleRetryFetch}
                        className="inline-flex items-center gap-2 rounded-full border border-destructive/60 px-3 py-1.5 text-xs font-semibold text-destructive transition hover:border-destructive hover:bg-destructive/10 hover:text-destructive/90"
                      >
                        Повторить попытку
                      </button>
                    </div>
                  </div>
                ) : null}
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
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
