import { useMemo, useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { Loader2Icon, SparklesIcon } from 'lucide-react'

import { fetchMealPlans } from '../../features/meal-plans/api'
import type { MealPlan } from '../../types/meal-plan'
import MealPlanCard from '../../features/market/cards/MealPlanCard'
import MarketPageHeader from '../../features/market/components/MarketPageHeader'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useSafeArea } from '../../hooks/useSafeArea'
import { Badge, Button, Card, EmptyState, RangeSlider, SearchInput, SegmentedControl } from '../../components/ui'

const GOAL_OPTIONS = [
  { value: '', label: 'Все цели' },
  { value: 'weight_loss', label: 'Похудение' },
  { value: 'muscle_gain', label: 'Масса' },
  { value: 'balanced', label: 'Баланс' },
  { value: 'detox', label: 'Детокс' },
  { value: 'keto', label: 'Кето' },
]

const DURATION_OPTIONS = [
  { value: '', label: 'Любая' },
  { value: '7', label: '7 дней' },
  { value: '14', label: '14 дней' },
  { value: '30', label: '30 дней' },
]

const CALORIE_RANGE: [number, number] = [1000, 3500]
const DEFAULT_CALORIE_RANGE: [number, number] = [1400, 2600]

function useMealPlanFilters() {
  const [search, setSearch] = useState('')
  const [goal, setGoal] = useState('')
  const [duration, setDuration] = useState('')
  const [calories, setCalories] = useState<[number, number]>(DEFAULT_CALORIE_RANGE)

  const debouncedSearch = useDebouncedValue(search.trim(), 320)

  return {
    search,
    setSearch,
    debouncedSearch,
    goal,
    setGoal,
    duration,
    setDuration,
    calories,
    setCalories,
  }
}

export function MarketMealPlansPage() {
  const safeArea = useSafeArea({ inset: 0, edges: ['bottom'] })
  const filters = useMealPlanFilters()

  const queryKey = useMemo(
    () => [
      'market-mealplans',
      {
        search: filters.debouncedSearch,
        goal: filters.goal,
        duration: filters.duration,
        calories: filters.calories,
      },
    ],
    [filters.debouncedSearch, filters.goal, filters.duration, filters.calories],
  )

  const query = useInfiniteQuery({
    queryKey,
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const page = typeof pageParam === 'number' && pageParam > 0 ? pageParam : 1
      const response = await fetchMealPlans({
        scope: 'public',
        page,
        search: filters.debouncedSearch || undefined,
        goal: filters.goal || undefined,
        duration: filters.duration || undefined,
        calories_min: filters.calories[0],
        calories_max: filters.calories[1],
        ordering: 'calories_per_day',
        page_size: 12,
      })
      return response
    },
    getNextPageParam: lastPage => {
      if (!lastPage.next) return null
      try {
        const url = new URL(lastPage.next, window.location.origin)
        const pageParam = url.searchParams.get('page')
        if (!pageParam) return null
        const parsed = Number.parseInt(pageParam, 10)
        return Number.isNaN(parsed) ? null : parsed
      } catch (_error) {
        return null
      }
    },
  })

  const plans = useMemo(
    () => (query.data?.pages ? query.data.pages.flatMap(page => page.results) : []),
    [query.data?.pages],
  )

  const handleResetFilters = () => {
    filters.setGoal('')
    filters.setDuration('')
    filters.setSearch('')
    filters.setCalories(DEFAULT_CALORIE_RANGE)
  }

  const hasActiveFilters =
    filters.goal ||
    filters.duration ||
    filters.debouncedSearch ||
    filters.calories[0] > DEFAULT_CALORIE_RANGE[0] ||
    filters.calories[1] < DEFAULT_CALORIE_RANGE[1]

  return (
    <div className="flex flex-col gap-6" style={safeArea}>
      <MarketPageHeader
        title="Готовые программы питания"
        description="Подборки рационов от нутрициологов и фитнес-кураторов: выберите цель, длительность и баланс калорий."
        action={
          query.data?.pages?.[0]?.count ? (
            <Badge tone="primary">{query.data.pages[0].count.toLocaleString('ru-RU')} планов</Badge>
          ) : null
        }
      />

      <Card className="flex flex-col gap-6 rounded-3xl border border-border/70 bg-card/80 p-5 shadow-level-2">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-1 flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Поиск</span>
            <SearchInput
              value={filters.search}
              onChange={event => filters.setSearch(event.target.value)}
              onClear={() => filters.setSearch('')}
              placeholder="Введите цель, ингредиент или описание"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <Button
              variant="secondary"
              size="sm"
              className="w-full min-w-[10rem] sm:w-auto"
              disabled={!hasActiveFilters}
              onClick={handleResetFilters}
            >
              Сбросить фильтры
            </Button>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          <div className="flex flex-col gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Цель</span>
            <SegmentedControl
              value={filters.goal}
              onValueChange={value => filters.setGoal(value ?? '')}
              options={GOAL_OPTIONS.map(option => ({ value: option.value, label: option.label }))}
              wrap
              className="w-full gap-2"
              itemClassName="flex-1 basis-[calc(50%-0.5rem)] sm:basis-auto"
            />
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Длительность</span>
            <SegmentedControl
              value={filters.duration}
              onValueChange={value => filters.setDuration(value ?? '')}
              options={DURATION_OPTIONS.map(option => ({ value: option.value, label: option.label }))}
              wrap
              className="w-full gap-2"
              itemClassName="flex-1 basis-[calc(50%-0.5rem)] sm:basis-auto"
            />
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Калорийность</span>
              <span className="text-xs text-muted-foreground">
                {filters.calories[0]} – {filters.calories[1]} ккал/день
              </span>
            </div>
            <RangeSlider
              value={filters.calories}
              onValueChange={value => filters.setCalories([value[0], value[1]])}
              min={CALORIE_RANGE[0]}
              max={CALORIE_RANGE[1]}
              step={50}
              className="px-1"
            />
          </div>
        </div>
      </Card>

      {query.isLoading ? (
        <div className="flex min-h-[16rem] items-center justify-center">
          <Loader2Icon className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
        </div>
      ) : query.isError ? (
        <Card className="border-destructive/40 bg-destructive/10 p-5 text-destructive">
          Не удалось загрузить программы питания. Попробуйте обновить страницу.
        </Card>
      ) : plans.length === 0 ? (
        <EmptyState
          title="Пока нет подходящих программ"
          description="Измените фильтры или вернитесь позже — мы готовим новые подборки."
          icon={<SparklesIcon className="h-6 w-6" aria-hidden="true" />}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {plans.map((plan: MealPlan) => (
            <MealPlanCard key={plan.id} plan={plan} to={`/market/meal-plans/${plan.id}`} />
          ))}
        </div>
      )}

      {query.hasNextPage ? (
        <div className="flex justify-center pt-2">
          <Button
            variant="secondary"
            size="lg"
            onClick={() => query.fetchNextPage()}
            loading={query.isFetchingNextPage}
          >
            Показать ещё
          </Button>
        </div>
      ) : null}
    </div>
  )
}

export default MarketMealPlansPage
