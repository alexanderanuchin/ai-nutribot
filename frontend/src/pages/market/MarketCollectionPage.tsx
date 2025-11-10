import { useCallback, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'
import { useInfiniteQuery, useMutation } from '@tanstack/react-query'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { RefreshCwIcon, ShoppingCartIcon, SparklesIcon, UtensilsCrossedIcon } from 'lucide-react'
import clsx from 'clsx'
import { isAxiosError } from 'axios'

import { fetchMarketCollection, type MarketCollectionItemMap, type MarketResource } from '../../api/market'
import { useMarketEvents } from '../../features/market/hooks/useMarketEvents'
import MarketListSkeleton from '../../features/market/components/MarketListSkeleton'
import { MarketFiltersSidebar, MarketFiltersMobileSheet } from '../../features/market/components/MarketFilters'
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
import {
  MARKET_AVAILABILITY_PARAMS,
  MARKET_ORDERING_MAP,
  MARKET_PRICE_LIMITS,
  MARKET_SORT_OPTIONS,
} from '../../features/market/filters/config'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { checkoutCart } from '../../features/market/cart/api'
import { useMarketCartStore, selectCartTotals } from '../../features/market/stores/cartStore'
import { useMarketPlanStore, selectPlanTotals } from '../../features/market/stores/planStore'
import { useSafeArea } from '../../hooks/useSafeArea'
import { useAuth } from '../../hooks/useAuth'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  SearchInput,
  useToast,
} from '../../components/ui'
import type { MarketCartCheckoutResponse, MarketQuickFilter } from '../../types/market'

interface MarketCollectionPageProps<T extends MarketResource> {
  resource: T
}

type MarketCardComponent<T extends MarketResource> = ComponentType<{ item: MarketCollectionItemMap[T] }>

const BANNER_AUTO_HIDE_MS = 12000

const FALLBACK_PRICE_RANGE: [number, number] = [0, 0]

const parseNumeric = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseFloat(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

interface FreshBannerProps {
  visible: boolean
  count: number
  resource: MarketResource
  refreshing: boolean
  onRefresh: () => void
  onDismiss: () => void
}

interface CartInsights {
  caloEquivalent: number | null
  caloRate: number | null
  caloBalance: number | null
  canPayWithCalo: boolean
  canCheckout: boolean
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
  insights,
  onCheckoutRub,
  onCheckoutCalo,
  checkoutMode,
}: {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
  insights: CartInsights
  onCheckoutRub: () => void
  onCheckoutCalo: () => void
  checkoutMode: 'rub' | 'calo' | null
}) {
  const priceFormatter = useMemo(
    () =>
      cart.currency
        ? new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: cart.currency,
            maximumFractionDigits: 0,
          })
        : null,
    [cart.currency],
  )
  const caloFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  )
  const rubSummary = cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : 'Добавьте продукты из каталога'
  const caloSummary =
    insights.caloEquivalent && insights.caloRate
      ? `≈ ${caloFormatter.format(insights.caloEquivalent)} CALO · ${caloFormatter.format(insights.caloRate)} ₽/CALO`
      : 'Настройте курс CaloCoin, чтобы видеть эквивалент'
  const caloBalanceHint =
    insights.caloBalance !== null
      ? `Баланс: ${caloFormatter.format(Math.max(0, insights.caloBalance))} CALO`
      : null
  const rubButtonLabel =
    cart.amount > 0 && priceFormatter ? `Оплатить ${priceFormatter.format(cart.amount)}` : 'Оформить заказ'
  const caloButtonLabel =
    insights.caloEquivalent && insights.caloEquivalent > 0
      ? `Оплатить ${caloFormatter.format(insights.caloEquivalent)} CALO`
      : 'Оплатить CaloCoin'

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
          <p className="text-sm text-muted-foreground">{rubSummary}</p>
          <p className="text-xs text-muted-foreground">{caloSummary}</p>
          {caloBalanceHint ? (
            <p className="text-xs text-muted-foreground">{caloBalanceHint}</p>
          ) : null}
          <div className="flex flex-col gap-2 pt-1">
            <Button
              type="button"
              variant="primary"
              size="md"
              onClick={onCheckoutRub}
              disabled={!insights.canCheckout || checkoutMode === 'calo'}
              loading={checkoutMode === 'rub'}
              title={!insights.canCheckout ? 'Добавьте товары в корзину, чтобы оформить заказ' : undefined}
            >
              {rubButtonLabel}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={onCheckoutCalo}
              disabled={!insights.canPayWithCalo || checkoutMode === 'rub'}
              loading={checkoutMode === 'calo'}
              title={
                !insights.canPayWithCalo
                  ? 'Недостаточно CaloCoin на счёте или не задан курс'
                  : undefined
              }
            >
              {caloButtonLabel}
            </Button>
          </div>
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
  insights,
  onFilters,
  onSearch,
  onCheckoutRub,
  onCheckoutCalo,
  checkoutMode,
}: {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
  insights: CartInsights
  onFilters: () => void
  onSearch: () => void
  onCheckoutRub: () => void
  onCheckoutCalo: () => void
  checkoutMode: 'rub' | 'calo' | null
}) {
  const safeArea = useSafeArea()
  const priceFormatter = cart.currency
    ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: cart.currency, maximumFractionDigits: 0 })
    : null
  const caloFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  )
  const rubAmount = cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : '0 ₽'
  const caloAmount =
    insights.caloEquivalent && insights.caloEquivalent > 0
      ? `${caloFormatter.format(insights.caloEquivalent)} CALO`
      : 'CaloCoin'
  const caloSummary =
    insights.caloRate && insights.caloEquivalent
      ? `≈ ${caloFormatter.format(insights.caloEquivalent)} CALO · ${caloFormatter.format(insights.caloRate)} ₽/CALO`
      : 'Курс CaloCoin пока не задан'

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 flex items-start justify-between gap-3 rounded-t-2xl border border-border/70 bg-card/95 px-4 py-3 shadow-level-3 backdrop-blur lg:hidden box-border max-w-[100vw] [overflow-x:clip]"
      style={{ paddingBottom: `calc(${safeArea.bottom}px + 0.75rem)` }}
    >
      <div className="flex flex-col gap-1">
        <Button variant="ghost" size="sm" className="min-w-[92px]" onClick={onFilters}>
          Фильтры
        </Button>
        <Button variant="ghost" size="sm" className="min-w-[92px]" onClick={onSearch}>
          Поиск
        </Button>
      </div>
      <div className="flex flex-1 flex-col gap-1 text-xs text-muted-foreground">
        <div className="flex items-center justify-between text-sm text-foreground">
          <span>Корзина · {cart.quantity}</span>
          <span>{rubAmount}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>План · {plan.count}</span>
          <span>{plan.servings > 0 ? `${plan.servings} порций` : 'Пусто'}</span>
        </div>
        <div className="text-[11px] text-muted-foreground">{caloSummary}</div>
      </div>
      <div className="flex flex-col gap-1">
        <Button
          type="button"
          variant="primary"
          size="sm"
          className="min-w-[120px] whitespace-nowrap"
          onClick={onCheckoutRub}
          disabled={!insights.canCheckout || checkoutMode === 'calo'}
          loading={checkoutMode === 'rub'}
        >
          Оплатить {rubAmount}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-w-[120px] whitespace-nowrap"
          onClick={onCheckoutCalo}
          disabled={!insights.canPayWithCalo || checkoutMode === 'rub'}
          loading={checkoutMode === 'calo'}
        >
          Оплатить {caloAmount}
        </Button>
      </div>
    </div>
  )
}

export function MarketCollectionPage<T extends MarketResource>({ resource }: MarketCollectionPageProps<T>) {
  const filterDefinitions = MARKET_FILTERS[resource] ?? []
  const [chipFilters, setChipFilters] = useState<Record<string, boolean>>({})
  const [priceRange, setPriceRange] = useState<[number, number]>(
    MARKET_PRICE_LIMITS[resource] ?? FALLBACK_PRICE_RANGE,
  )
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
  const isLaptopUp = useMediaQuery('(min-width: 1280px)')
  const { profile } = useAuth()
  const { notify } = useToast()

  const cartTotals = useMarketCartStore(
    selectCartTotals,
    (a, b) => a.count === b.count && a.quantity === b.quantity && a.amount === b.amount && a.currency === b.currency,
  )
  const serverCart = useMarketCartStore(state => state.serverCart)
  const clearCart = useMarketCartStore(state => state.clear)
  const planTotals = useMarketPlanStore(
    selectPlanTotals,
    (a, b) => a.count === b.count && a.servings === b.servings && a.calories === b.calories,
  )

  const caloRate = parseNumeric(profile?.calocoin_rate_rub)
  const caloBalance = parseNumeric(profile?.calocoin_balance)
  const caloEquivalent =
    caloRate && caloRate > 0 && cartTotals.amount > 0 ? cartTotals.amount / caloRate : null
  const canCheckoutRub = cartTotals.amount > 0 && Boolean(serverCart)
  const canPayWithCalo = Boolean(
    canCheckoutRub &&
      caloEquivalent !== null &&
      caloBalance !== null &&
      caloBalance + 1e-6 >= caloEquivalent,
  )
  const cartInsights = useMemo<CartInsights>(
    () => ({
      caloEquivalent,
      caloRate,
      caloBalance,
      canPayWithCalo,
      canCheckout: canCheckoutRub,
    }),
    [caloEquivalent, caloRate, caloBalance, canPayWithCalo, canCheckoutRub],
  )

  const checkoutMutation = useMutation<
    MarketCartCheckoutResponse,
    unknown,
    { cartId: number; mode: 'rub' | 'calo' }
  >({
    mutationFn: async ({ cartId, mode }) => {
      const metadata = { source: 'market' }
      const payload =
        mode === 'calo'
          ? { pay_with_wallet: true, wallet_currency: 'CALO' as const, metadata }
          : { metadata }
      return checkoutCart(cartId, payload)
    },
    onSuccess: (response, variables) => {
      if (variables.mode === 'calo' && response.paid) {
        notify({
          title: 'Заказ оплачен',
          description: `Списано ${response.order.amount} CALO`,
          tone: 'success',
        })
      } else {
        notify({
          title: 'Заказ создан',
          description: 'Мы зафиксировали корзину — оплатите заказ в разделе «Заказы».',
          tone: 'success',
        })
      }
      clearCart()
    },
    onError: error => {
      let message = 'Не удалось оформить заказ'
      if (isAxiosError(error)) {
        const data = error.response?.data as any
        if (data) {
          if (typeof data.detail === 'string') {
            message = data.detail
          } else if (typeof data.pay_with_wallet === 'string') {
            message = data.pay_with_wallet
          }
        }
      } else if (error instanceof Error) {
        message = error.message
      }
      notify({ title: 'Ошибка оформления', description: message, tone: 'destructive' })
    },
  })

  const checkoutMode = checkoutMutation.isPending ? checkoutMutation.variables?.mode ?? null : null

  const handleCheckoutRub = useCallback(() => {
    if (!serverCart) {
      notify({
        title: 'Корзина не синхронизирована',
        description: 'Добавьте товары и обновите корзину перед оформлением.',
      })
      return
    }
    checkoutMutation.mutate({ cartId: serverCart.id, mode: 'rub' })
  }, [checkoutMutation, notify, serverCart])

  const handleCheckoutCalo = useCallback(() => {
    if (!serverCart) {
      notify({
        title: 'Корзина не синхронизирована',
        description: 'Добавьте товары и обновите корзину перед оформлением.',
      })
      return
    }
    if (!canPayWithCalo) {
      notify({
        title: 'Недостаточно CaloCoin',
        description: 'Пополните кошелёк или задайте курс CaloCoin в профиле.',
        tone: 'warning',
      })
      return
    }
    checkoutMutation.mutate({ cartId: serverCart.id, mode: 'calo' })
  }, [checkoutMutation, notify, serverCart, canPayWithCalo])

  useEffect(() => {
    setChipFilters({})
    setPriceRange(MARKET_PRICE_LIMITS[resource] ?? FALLBACK_PRICE_RANGE)
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
    if (filtersOpen && isLaptopUp) {
      setFiltersOpen(false)
    }
  }, [filtersOpen, isLaptopUp])

  const filterParams = useMemo(() => {
    const params: Record<string, string | number | boolean> = {}
    const availabilityParam = MARKET_AVAILABILITY_PARAMS[resource]
    const priceLimits = MARKET_PRICE_LIMITS[resource]
    filterDefinitions.forEach(definition => {
      if (!chipFilters[definition.id]) return
      const existing = params[definition.param]
      if (existing == null) {
        params[definition.param] = definition.value
        return
      }
      params[definition.param] = `${String(existing)},${String(definition.value)}`
    })
    if (priceLimits) {
      const [minPrice, maxPrice] = priceLimits
      if (priceRange[0] > minPrice) {
        params.min_price = priceRange[0]
      }
      if (priceRange[1] < maxPrice) {
        params.max_price = priceRange[1]
      }
    }
    if (ratingValue > 0) {
      params.min_rating = ratingValue
    }
    if (availability === 'available' && availabilityParam) {
      params[availabilityParam] = true
    }
    const ordering = MARKET_ORDERING_MAP[resource]?.[sortValue]
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
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const pageNumber = typeof pageParam === 'number' && pageParam > 0 ? pageParam : 1
      const { items, nextPage, raw } = await fetchMarketCollection({
        resource,
        page: pageNumber,
        filters: filterParams,
        search: debouncedSearch.trim() || undefined,
        pageSize: resource === 'stores' ? 10 : 12,
      })
      return { items, nextPage, raw }
    },
    getNextPageParam: lastPage => lastPage.nextPage,
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
    setPriceRange(MARKET_PRICE_LIMITS[resource] ?? FALLBACK_PRICE_RANGE)
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

  useMarketEvents({
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
      availabilityEnabled: Boolean(MARKET_AVAILABILITY_PARAMS[resource]),
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

  const renderSearchControl = useCallback(() => {
    if (isTabletUp) {
      return (
        <MarketSearch
          ref={searchHandleRef}
          resource={resource}
          value={searchValue}
          onSubmit={setSearchValue}
          onQuickFilterSelect={handleQuickFilterSelect}
        />
      )
    }
    return (
      <SearchInput
        ref={searchInputRef}
        value={searchValue}
        onChange={event => setSearchValue(event.target.value)}
        placeholder="Поиск по названию, ингредиентам или тегам"
        onClear={() => setSearchValue('')}
        className="max-w-full"
      />
    )
  }, [
    handleQuickFilterSelect,
    isTabletUp,
    resource,
    searchValue,
    setSearchValue,
  ])

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
          'relative flex flex-col gap-4 lg:gap-5 xl:gap-6',
          isLaptopUp ? 'xl:sticky xl:top-0 xl:z-40 xl:pb-4' : '',
        )}
      >
        <div className="relative xl:z-40">
          <MarketPageHeader
            title={MARKET_RESOURCE_TITLE[resource]}
            description={MARKET_RESOURCE_DESCRIPTION[resource]}
            action={
              totalAvailable ? (
                <Badge tone="primary">{totalAvailable.toLocaleString('ru-RU')} {MARKET_RESOURCE_LABELS[resource]}</Badge>
              ) : null
            }
          >
            {!isLaptopUp ? (
              <div className={clsx('flex flex-col gap-3', isTabletUp ? 'lg:flex-row lg:items-center lg:justify-between' : '')}>
                <div className="w-full">{renderSearchControl()}</div>
              </div>
            ) : null}
          </MarketPageHeader>
        </div>
        {!isLaptopUp ? (
          <MarketFiltersMobileSheet
            {...filterComponentProps}
            open={filtersOpen}
            onOpenChange={setFiltersOpen}
          />
        ) : null}
      </div>

      <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:gap-8">
        <div className="flex flex-col gap-6 xl:mt-6">
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

          <AnimatePresence>
            {isFetchingNextPage ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <MarketListSkeleton variant={skeletonVariant} count={resource === 'stores' ? 2 : 3} />
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div ref={sentinelRef} aria-hidden="true" className="h-px w-full" />
        </div>
        <aside className="hidden xl:block xl:sticky xl:top-28">
          <div className="flex flex-col gap-6">
            <MarketFiltersSidebar
              {...filterComponentProps}
              searchControl={isLaptopUp ? renderSearchControl() : undefined}
            />
            <FloatingSummary
              cart={cartTotals}
              plan={planTotals}
              insights={cartInsights}
              onCheckoutRub={handleCheckoutRub}
              onCheckoutCalo={handleCheckoutCalo}
              checkoutMode={checkoutMode}
            />
          </div>
        </aside>
      </div>

      <MobileSummaryBar
        cart={cartTotals}
        plan={planTotals}
        insights={cartInsights}
        onFilters={() => setFiltersOpen(true)}
        onSearch={() => {
          if (isTabletUp) {
            searchHandleRef.current?.openExtended()
            return
          }
          searchInputRef.current?.focus()
          window.scrollTo({ top: 0, behavior: 'smooth' })
        }}
        onCheckoutRub={handleCheckoutRub}
        onCheckoutCalo={handleCheckoutCalo}
        checkoutMode={checkoutMode}
      />
    </div>
  )
}

export default MarketCollectionPage
export { FreshBanner }
