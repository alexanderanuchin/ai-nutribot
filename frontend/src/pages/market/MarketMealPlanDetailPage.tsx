import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeftIcon, CalendarDaysIcon, ClockIcon, FlameIcon, LayersIcon, SparklesIcon, StarIcon } from 'lucide-react'

import { useMealPlanQuery } from '../../features/meal-plans/hooks'
import type { MealPlan, MealPlanItem } from '../../types/meal-plan'
import MarketPageHeader from '../../features/market/components/MarketPageHeader'
import { Badge, Button, Card, EmptyState, Skeleton } from '../../components/ui'

const GOAL_LABELS: Record<string, string> = {
  weight_loss: 'Похудение',
  muscle_gain: 'Набор массы',
  detox: 'Детокс',
  keto: 'Кето',
  balanced: 'Сбалансированное питание',
}

function formatPrice(plan: MealPlan): string {
  if (plan.is_free ?? plan.price_stars == null) {
    return 'Бесплатно'
  }
  if (plan.price_stars != null) {
    return `${plan.price_stars.toLocaleString('ru-RU')} Stars`
  }
  if (plan.price_amount) {
    const amount = Number.parseFloat(plan.price_amount)
    if (Number.isFinite(amount)) {
      return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: plan.price_currency || 'RUB',
        maximumFractionDigits: 0,
      }).format(amount)
    }
  }
  return '—'
}

function groupItemsByDay(items: MealPlanItem[]): Array<{ key: string; title: string; items: MealPlanItem[] }> {
  const map = new Map<string, MealPlanItem[]>()
  items.forEach(item => {
    const dateKey = item.scheduled_for ?? 'unscheduled'
    if (!map.has(dateKey)) {
      map.set(dateKey, [])
    }
    map.get(dateKey)!.push(item)
  })
  const sortedKeys = Array.from(map.keys()).sort((a, b) => {
    if (a === 'unscheduled') return 1
    if (b === 'unscheduled') return -1
    return a.localeCompare(b)
  })
  return sortedKeys.map(key => {
    const date = key === 'unscheduled' ? null : new Date(key)
    const title = date
      ? date.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
      : 'Без даты'
    return { key, title, items: map.get(key) ?? [] }
  })
}

export function MarketMealPlanDetailPage() {
  const params = useParams<{ planId: string }>()
  const planId = Number.parseInt(params.planId ?? '', 10)
  const planQuery = useMealPlanQuery(Number.isFinite(planId) ? planId : 0, {
    enabled: Number.isFinite(planId) && planId > 0,
  })

  const groupedItems = useMemo(() => {
    if (!planQuery.data) return []
    return groupItemsByDay(planQuery.data.items)
  }, [planQuery.data])

  if (!Number.isFinite(planId) || planId <= 0) {
    return (
      <EmptyState
        title="План не найден"
        description="Указанная программа недоступна. Вернитесь в каталог и выберите другую."
        icon={<SparklesIcon className="h-6 w-6" aria-hidden="true" />}
      />
    )
  }

  if (planQuery.isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-24 w-full rounded-3xl" />
        <Skeleton className="h-64 w-full rounded-3xl" />
      </div>
    )
  }

  if (planQuery.isError || !planQuery.data) {
    return (
      <EmptyState
        title="Не удалось загрузить программу"
        description="Попробуйте обновить страницу или выберите другую программу."
        icon={<SparklesIcon className="h-6 w-6" aria-hidden="true" />}
      />
    )
  }

  const plan = planQuery.data
  const goalLabel = plan.goal ? GOAL_LABELS[plan.goal] ?? plan.goal : null
  const priceLabel = formatPrice(plan)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/market/meal-plans">
            <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" /> Назад
          </Link>
        </Button>
        <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Программа питания</span>
      </div>

      <MarketPageHeader
        title={plan.title}
        description={plan.description || 'Персонализированная программа питания от эксперта NutriBot.'}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="primary" className="gap-1">
              <StarIcon className="h-4 w-4" aria-hidden="true" />
              {priceLabel}
            </Badge>
            {goalLabel ? <Badge tone="secondary">{goalLabel}</Badge> : null}
            {plan.duration_days ? (
              <Badge tone="secondary" className="gap-1">
                <CalendarDaysIcon className="h-4 w-4" aria-hidden="true" />
                {plan.duration_days} дн.
              </Badge>
            ) : null}
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:items-start">
        <div className="space-y-4">
          {groupedItems.map(day => (
            <Card key={day.key} className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/80 p-5 shadow-level-2">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-foreground capitalize">{day.title}</h3>
                <Badge tone="muted" className="gap-1">
                  <ClockIcon className="h-4 w-4" aria-hidden="true" />
                  {day.items.length} приёма
                </Badge>
              </div>
              <div className="flex flex-col gap-3">
                {day.items.map(item => {
                  const reference = item.recipe_snapshot || item.product_snapshot
                  const typeLabel = item.recipe_snapshot ? 'Рецепт' : 'Продукт'
                  return (
                    <Card
                      key={item.id}
                      className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-background/70 p-4 shadow-level-1"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-sm font-semibold text-foreground">
                            {reference?.title || 'Без названия'}
                          </span>
                          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">{typeLabel}</span>
                        </div>
                        <Badge tone="secondary" className="gap-1">
                          <LayersIcon className="h-4 w-4" aria-hidden="true" />
                          {item.servings} порций
                        </Badge>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                        {item.meal_type ? <Badge tone="muted">{item.meal_type}</Badge> : null}
                        <span className="inline-flex items-center gap-1">
                          <FlameIcon className="h-3.5 w-3.5" aria-hidden="true" />
                          {Math.round(item.total_nutrition.calories)} ккал
                        </span>
                        <span>Б {Math.round(item.total_nutrition.protein_g)} г</span>
                        <span>Ж {Math.round(item.total_nutrition.fat_g)} г</span>
                        <span>У {Math.round(item.total_nutrition.carbs_g)} г</span>
                      </div>
                    </Card>
                  )
                })}
              </div>
            </Card>
          ))}
        </div>

        <aside className="flex flex-col gap-4">
          <Card className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/90 p-5 shadow-level-2">
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Сводка</span>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FlameIcon className="h-4 w-4" aria-hidden="true" />
                {Math.round(plan.nutrition_totals.calories)} ккал · в среднем{' '}
                {plan.calories_per_day ? `${Math.round(plan.calories_per_day)} ккал/день` : 'гибкий график'}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-3">
                <span className="text-xs text-muted-foreground">Белки</span>
                <span className="text-lg font-semibold text-foreground">
                  {Math.round(plan.nutrition_totals.protein_g)} г
                </span>
              </div>
              <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-3">
                <span className="text-xs text-muted-foreground">Жиры</span>
                <span className="text-lg font-semibold text-foreground">{Math.round(plan.nutrition_totals.fat_g)} г</span>
              </div>
              <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-3">
                <span className="text-xs text-muted-foreground">Углеводы</span>
                <span className="text-lg font-semibold text-foreground">{Math.round(plan.nutrition_totals.carbs_g)} г</span>
              </div>
              <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-3">
                <span className="text-xs text-muted-foreground">Приёмов</span>
                <span className="text-lg font-semibold text-foreground">{plan.items.length}</span>
              </div>
            </div>
            <Button asChild variant="primary">
              <Link to="/nutrition/builder">Открыть в конструкторе</Link>
            </Button>
          </Card>

          <Card className="rounded-3xl border border-border/70 bg-card/70 p-5 shadow-level-1">
            <h4 className="text-sm font-semibold text-foreground">Поделиться</h4>
            <p className="mt-2 text-xs text-muted-foreground">
              Расскажите друзьям или клиентам о программе: поделитесь ссылкой на страницу или экспортируйте план в разделе "Экспорт" в конструкторе.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  )
}

export default MarketMealPlanDetailPage
