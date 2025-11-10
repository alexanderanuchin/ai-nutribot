import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon, CalendarDaysIcon, ClockIcon, FlameIcon, LayersIcon, SparklesIcon, StarIcon } from 'lucide-react'
import { isAxiosError } from 'axios'

import { useMealPlanQuery, usePurchaseMealPlanMutation } from '../../features/meal-plans/hooks'
import type { MealPlan, MealPlanItem } from '../../types/meal-plan'
import MarketPageHeader from '../../features/market/components/MarketPageHeader'
import { Badge, Button, Card, EmptyState, Skeleton, useToast } from '../../components/ui'

const GOAL_LABELS: Record<string, string> = {
  weight_loss: 'Похудение',
  muscle_gain: 'Набор массы',
  detox: 'Детокс',
  keto: 'Кето',
  balanced: 'Сбалансированное питание',
}

function formatPrice(plan: MealPlan): string {
  if (plan.is_free ?? plan.price_stars == null) return 'Бесплатно'
  if (plan.price_stars != null) return `${plan.price_stars.toLocaleString('ru-RU')} Stars`
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
  return 'По запросу'
}

function groupItemsByDay(items: MealPlanItem[]): Array<{ key: string; title: string; items: MealPlanItem[] }> {
  const map = new Map<string, MealPlanItem[]>()
  items.forEach(item => {
    const dateKey = item.scheduled_for ?? 'unscheduled'
    if (!map.has(dateKey)) map.set(dateKey, [])
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
  const navigate = useNavigate()
  const { notify } = useToast()
  const safePlanId = Number.isFinite(planId) && planId > 0 ? planId : 0

  const planQuery = useMealPlanQuery(Number.isFinite(planId) ? planId : 0, {
    enabled: Number.isFinite(planId) && planId > 0,
  })

  const purchaseMutation = usePurchaseMealPlanMutation(safePlanId, {
    onSuccess: () => {
      notify({
        title: 'Программа доступна',
        description: 'Мы открыли доступ к программе. Она появится в вашем разделе «Программы».',
        tone: 'success',
      })
    },
    onError: error => {
      let message = 'Не удалось получить доступ к программе'
      if (isAxiosError(error)) {
        const data = error.response?.data as any
        if (typeof data?.detail === 'string') message = data.detail
        else if (typeof data?.code === 'string' && data.code === 'insufficient_stars') {
          message = 'Недостаточно Stars для покупки программы. Пополните кошелёк и попробуйте снова.'
        }
      } else if (error instanceof Error) {
        message = error.message
      }
      notify({ title: 'Ошибка покупки', description: message, tone: 'destructive' })
    },
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
  const hasAccess = Boolean(plan.has_access || plan.is_free)
  const purchaseButtonLabel = hasAccess
    ? 'Открыть программу'
    : plan.price_stars != null || plan.price_amount
      ? `Получить за ${priceLabel}`
      : 'Получить доступ'

  const handlePurchase = () => {
    if (hasAccess) {
      navigate('/nutrition/builder')
      return
    }
    if (safePlanId <= 0) {
      notify({ title: 'Недоступно', description: 'План не найден, обновите страницу и попробуйте снова.' })
      return
    }
    purchaseMutation.mutate()
  }

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

      <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_340px] xl:items-start xl:gap-6">
        <div className="flex flex-col gap-4">
          {groupedItems.map(group => (
            <Card key={group.key} className="flex flex-col gap-3 rounded-3xl border border-border/70 bg-card/80 p-5 shadow-level-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-foreground">{group.title}</h3>
                <Badge tone="secondary" className="gap-1">
                  <ClockIcon className="h-4 w-4" aria-hidden="true" />
                  {group.items.length} приемов
                </Badge>
              </div>
              <div className="grid gap-3">
                {group.items.map(item => {
                  return (
                    <Card key={item.id} className="flex items-center justify-between gap-3 rounded-2xl border border-border/60 bg-background/60 p-4">
                      <div className="flex min-w-0 flex-col">
                        <span className="truncate text-sm font-semibold text-foreground">{item.recipe_title}</span>
                        <span className="truncate text-xs text-muted-foreground">{item.notes || '—'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="inline-flex items-center gap-1">
                          <FlameIcon className="h-3.5 w-3.5" aria-hidden="true" />
                          {Math.round(item.total_nutrition.calories)} ккал
                        </div>
                        <Badge tone="secondary" className="gap-1">
                          <LayersIcon className="h-4 w-4" aria-hidden="true" />
                          {item.servings} порций
                        </Badge>
                      </div>
                    </Card>
                  )
                })}
              </div>
            </Card>
          ))}
        </div>

        <aside className="flex flex-col gap-4">
          <Card className="flex flex-col gap-4 rounded-3xl border border-border/70 bg-card/95 p-5 shadow-level-2">
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Доступ</span>
              <div className="flex items-center gap-2 text-lg font-semibold text-foreground">
                {priceLabel}
                {hasAccess ? <Badge tone="success">Уже куплено</Badge> : null}
              </div>
              <p className="text-sm text-muted-foreground">
                {hasAccess
                  ? 'Вы можете открыть программу в конструкторе и настроить её под себя.'
                  : 'После покупки программа появится в ваших материалах, а доступ откроется мгновенно.'}
              </p>
            </div>
            <Button
              type="button"
              variant={hasAccess ? 'success' : 'primary'}
              size="md"
              onClick={handlePurchase}
              loading={purchaseMutation.isPending}
              leadingIcon={hasAccess ? <SparklesIcon className="h-4 w-4" aria-hidden="true" /> : <StarIcon className="h-4 w-4" aria-hidden="true" />}
            >
              {purchaseButtonLabel}
            </Button>
            {!hasAccess ? (
              <p className="text-xs text-muted-foreground">
                Оплата производится Stars в кошельке NutriBot. При нехватке средств пополните баланс и повторите попытку.
              </p>
            ) : null}
          </Card>

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
            <Button asChild variant="secondary" disabled={!hasAccess}>
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
