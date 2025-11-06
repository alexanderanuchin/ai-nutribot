import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { XIcon } from 'lucide-react'

import { Button, Card, IconButton, Skeleton } from '../../../components/ui'
import type { MealPlan, MealPlanNutritionTotals } from '../../../types/meal-plan'
import { computeDailyAverageNutrition, formatNutritionValue, getPlanDurationDays } from '../utils'
import { useMealPlanQuery } from '../hooks'

interface ComparisonModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  planIds: number[]
}

const metrics: Array<{
  key: keyof MealPlanNutritionTotals
  label: string
  precision?: number
}> = [
  { key: 'calories', label: 'Калории (ккал/день)', precision: 0 },
  { key: 'protein_g', label: 'Белки (г/день)', precision: 0 },
  { key: 'fat_g', label: 'Жиры (г/день)', precision: 0 },
  { key: 'carbs_g', label: 'Углеводы (г/день)', precision: 0 },
]

const dayPluralRules = new Intl.PluralRules('ru-RU')

function formatDuration(days: number): string {
  if (!days) return '—'
  const rule = dayPluralRules.select(days)
  switch (rule) {
    case 'one':
      return `${days} день`
    case 'few':
      return `${days} дня`
    default:
      return `${days} дней`
  }
}

function formatPrice(plan: MealPlan | null): { label: string; value: number | null } {
  if (!plan || plan.price_amount == null || plan.price_amount === '') {
    return { label: 'Бесплатно', value: 0 }
  }

  const numeric = Number(plan.price_amount)
  const currency = plan.price_currency || 'RUB'

  if (!Number.isFinite(numeric)) {
    return { label: `${plan.price_amount} ${currency}`.trim(), value: null }
  }

  try {
    const formatter = new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    })
    return { label: formatter.format(numeric), value: numeric }
  } catch (error) {
    return { label: `${numeric} ${currency}`.trim(), value: numeric }
  }
}

function getMetricTone(
  values: Array<MealPlanNutritionTotals | null>,
  index: number,
  key: keyof MealPlanNutritionTotals,
) {
  const current = values[index]?.[key]
  const otherIndex = index === 0 ? 1 : 0
  const other = values[otherIndex]?.[key]

  if (current == null || other == null) {
    return 'text-foreground'
  }

  if (current > other) {
    return 'text-emerald-500 font-semibold'
  }

  if (current < other) {
    return 'text-muted-foreground'
  }

  return 'text-foreground'
}

function getPriceTone(values: Array<number | null>, index: number) {
  const current = values[index]
  const otherIndex = index === 0 ? 1 : 0
  const other = values[otherIndex]

  if (current == null || other == null) {
    return 'text-foreground'
  }

  if (current < other) {
    return 'text-emerald-500 font-semibold'
  }

  if (current > other) {
    return 'text-muted-foreground'
  }

  return 'text-foreground'
}

export default function ComparisonModal({ open, onOpenChange, planIds }: ComparisonModalProps) {
  const [firstPlanId, secondPlanId] = planIds

  const firstPlanQuery = useMealPlanQuery(firstPlanId ?? null, {
    enabled: open && typeof firstPlanId === 'number',
  })
  const secondPlanQuery = useMealPlanQuery(secondPlanId ?? null, {
    enabled: open && typeof secondPlanId === 'number',
  })

  const queries = [firstPlanQuery, secondPlanQuery]

  const plans: Array<MealPlan | null> = [firstPlanQuery.data ?? null, secondPlanQuery.data ?? null]

  const dailyAverages = plans.map(plan => (plan ? computeDailyAverageNutrition(plan) : null))
  const priceInfo = plans.map(plan => formatPrice(plan))
  const durationInfo = plans.map(plan => (plan ? getPlanDurationDays(plan) : 0))
  const priceValues = priceInfo.map(info => info.value)

  const anyError = queries.find(query => query.error)

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="fixed inset-0 z-[80] bg-black/40 backdrop-blur"
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 24 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="fixed inset-0 z-[81] flex items-start justify-center overflow-y-auto p-6"
              >
                <Card className="flex w-full max-w-5xl flex-col gap-6 border-border/70 bg-background/95 p-6 shadow-level-3">
                  <div className="flex items-start justify-between gap-4 border-b border-border/60 pb-4">
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-foreground">Сравнение планов</Dialog.Title>
                      <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                        Сопоставьте ключевые показатели питания и стоимость выбранных программ.
                      </Dialog.Description>
                    </div>
                    <Dialog.Close asChild>
                      <IconButton variant="ghost" size="sm" aria-label="Закрыть">
                        <XIcon className="h-4 w-4" aria-hidden="true" />
                      </IconButton>
                    </Dialog.Close>
                  </div>

                  {anyError ? (
                    <div className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                      Не удалось загрузить данные планов. Попробуйте ещё раз позже.
                    </div>
                  ) : (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {plans.map((plan, index) => {
                        const query = queries[index]
                        const averages = dailyAverages[index]
                        const price = priceInfo[index]
                        const duration = durationInfo[index]
                        return (
                          <Card
                            key={plan?.id ?? `placeholder-${index}`}
                            className="space-y-4 border-border/60 bg-card/80 p-5 shadow-level-2"
                          >
                            {query.isLoading ? (
                              <div className="space-y-4">
                                <Skeleton className="h-5 w-3/4" />
                                <div className="space-y-2">
                                  {metrics.map(metric => (
                                    <Skeleton key={metric.key} className="h-4 w-full" />
                                  ))}
                                </div>
                                <Skeleton className="h-4 w-1/2" />
                              </div>
                            ) : plan ? (
                              <div className="space-y-4">
                                <div>
                                  <div className="text-xs uppercase text-muted-foreground">План {index + 1}</div>
                                  <div className="mt-1 text-base font-semibold text-foreground">{plan.title}</div>
                                  <div className="mt-1 text-xs text-muted-foreground">
                                    {new Date(plan.start_date).toLocaleDateString('ru-RU', {
                                      day: 'numeric',
                                      month: 'long',
                                    })}
                                  </div>
                                </div>
                                <dl className="space-y-3">
                                  {metrics.map(metric => (
                                    <div key={metric.key} className="flex items-center justify-between gap-3">
                                      <dt className="text-xs text-muted-foreground">{metric.label}</dt>
                                      <dd
                                        className={`text-sm ${getMetricTone(dailyAverages, index, metric.key)}`}
                                      >
                                        {averages
                                          ? formatNutritionValue(
                                              averages[metric.key],
                                              metric.precision ?? 0,
                                            )
                                          : '—'}
                                      </dd>
                                    </div>
                                  ))}
                                  <div className="flex items-center justify-between gap-3">
                                    <dt className="text-xs text-muted-foreground">Стоимость</dt>
                                    <dd className={`text-sm ${getPriceTone(priceValues, index)}`}>
                                      {price.label}
                                    </dd>
                                  </div>
                                  <div className="flex items-center justify-between gap-3">
                                    <dt className="text-xs text-muted-foreground">Длительность</dt>
                                    <dd className="text-sm font-medium text-foreground">{formatDuration(duration)}</dd>
                                  </div>
                                </dl>
                              </div>
                            ) : (
                              <div className="text-sm text-muted-foreground">План не найден или недоступен.</div>
                            )}
                          </Card>
                        )
                      })}
                    </div>
                  )}

                  <div className="flex justify-end border-t border-border/60 pt-4">
                    <Dialog.Close asChild>
                      <Button type="button" variant="outline">
                        Закрыть
                      </Button>
                    </Dialog.Close>
                  </div>
                </Card>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}
