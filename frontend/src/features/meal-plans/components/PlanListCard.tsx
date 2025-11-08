import { CalendarIcon, GlobeIcon, LockIcon, PlusCircleIcon, StarIcon, Trash2Icon } from 'lucide-react'
import clsx from 'clsx'
import { useMemo, useState, type ReactNode } from 'react'

import { Badge, Button, Card, ConfirmDialog, IconButton, Rating, Skeleton } from '../../../components/ui'
import type { MealPlan } from '../../../types/meal-plan'
import { formatNutritionValue } from '../utils'
import { computeDaysUntilReview, parsePlanDescription } from '../planDescription'

interface PlanListCardProps {
  plans: MealPlan[]
  selectedPlanId: number | null
  onSelectPlan: (planId: number) => void
  onCreatePlan: () => void
  onDeletePlan: (planId: number) => void
  selectedPlans: number[]
  onToggleSelectPlan: (planId: number) => void
  onCompareSelected: () => void
  isLoading?: boolean
  isCreating?: boolean
  deletingPlanId?: number | null
  isDeleting?: boolean
}

export function PlanListCard({
  plans,
  selectedPlanId,
  onSelectPlan,
  onCreatePlan,
  onDeletePlan,
  selectedPlans,
  onToggleSelectPlan,
  onCompareSelected,
  isLoading = false,
  isCreating = false,
  deletingPlanId = null,
  isDeleting = false,
}: PlanListCardProps) {
  const [pendingPlanId, setPendingPlanId] = useState<number | null>(null)

  const pendingPlan = useMemo(() => plans.find(plan => plan.id === pendingPlanId) ?? null, [plans, pendingPlanId])

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-muted-foreground">Мои планы</div>
          <div className="text-foreground">Управляйте вариантами питания</div>
        </div>
        <Button
          variant="primary"
          size="sm"
          leadingIcon={<PlusCircleIcon className="h-4 w-4" aria-hidden="true" />}
          onClick={onCreatePlan}
          loading={isCreating}
        >
          Новый план
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : plans.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/60 bg-muted/20 px-3 py-6 text-center text-xs text-muted-foreground">
          У вас пока нет сохранённых планов. Создайте первый, чтобы приступить к настройке.
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {plans.map(plan => {
              const isActive = plan.id === selectedPlanId
              const priceStars = Number.isFinite(plan.price_stars ?? Number.NaN)
                ? Number(plan.price_stars)
                : null
              const isFree = plan.is_free ?? priceStars == null
              const price = isFree
                ? 'Free'
                : `${priceStars!.toLocaleString('ru-RU')} Stars`
              const isSelectedForCompare = selectedPlans.includes(plan.id)
              const selectionDisabled = !isSelectedForCompare && selectedPlans.length >= 2
              const descriptionSchema = parsePlanDescription(plan.description)
              const daysToReview = computeDaysUntilReview(descriptionSchema.sections.nextReviewDate)
              const ratingValue = Number.isFinite(Number(plan.metadata?.rating ?? Number.NaN))
                ? Number(plan.metadata?.rating)
                : null
              const ratingCount = Number.isFinite(Number(plan.metadata?.rating_count ?? Number.NaN))
                ? Math.trunc(Number(plan.metadata?.rating_count))
                : null
              let reviewBadge: ReactNode = null
              if (typeof daysToReview === 'number') {
                if (daysToReview < 0) {
                  reviewBadge = (
                    <Badge variant="destructive" className="gap-1 text-[10px] uppercase">
                      Просрочен {Math.abs(daysToReview)} дн.
                    </Badge>
                  )
                } else if (daysToReview <= 3) {
                  reviewBadge = (
                    <Badge variant="secondary" className="gap-1 text-[10px] uppercase">
                      Пересмотр через {daysToReview} дн.
                    </Badge>
                  )
                } else {
                  reviewBadge = (
                    <Badge variant="outline" className="gap-1 text-[10px] uppercase">
                      Контроль {descriptionSchema.sections.nextReviewDate}
                    </Badge>
                  )
                }
              }
              return (
              <div
                key={plan.id}
                role="button"
                onClick={() => onSelectPlan(plan.id)}
                className={clsx(
                  'flex items-center justify-between gap-3 rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-left shadow-level-1 transition hover:border-primary/60 hover:shadow-level-2',
                  isActive && 'border-primary/70 shadow-level-3'
                )}
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <div className="pt-1">
                    <input
                      type="checkbox"
                      checked={isSelectedForCompare}
                      disabled={selectionDisabled}
                      onChange={event => {
                        event.stopPropagation()
                        onToggleSelectPlan(plan.id)
                      }}
                      onClick={event => event.stopPropagation()}
                      className="h-4 w-4 accent-primary"
                      aria-label={
                        isSelectedForCompare ? 'Исключить план из сравнения' : 'Добавить план к сравнению'
                      }
                    />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="truncate text-sm font-semibold text-foreground">{plan.title}</div>
                      <Badge variant={plan.is_published ? 'outline' : 'secondary'} className="gap-1 text-[10px] uppercase">
                        {plan.is_published ? (
                          <GlobeIcon className="h-3.5 w-3.5" aria-hidden="true" />
                        ) : (
                          <LockIcon className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        {plan.is_published ? 'Публичный' : 'Черновик'}
                      </Badge>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <CalendarIcon className="h-3.5 w-3.5" aria-hidden="true" />
                        {new Date(plan.start_date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        {!isFree ? <StarIcon className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" /> : null}
                        {price}
                      </span>
                      <span>{formatNutritionValue(plan.nutrition_totals.calories, 0)} ккал</span>
                      {reviewBadge}
                      {ratingValue ? <Rating value={ratingValue} count={ratingCount ?? undefined} size="sm" /> : null}
                    </div>
                  </div>
                </div>
                <IconButton
                  variant="ghost"
                  size="sm"
                  aria-label="Удалить план"
                  onClick={event => {
                    event.stopPropagation()
                    setPendingPlanId(plan.id)
                  }}
                  disabled={isDeleting && deletingPlanId === plan.id}
                >
                  <Trash2Icon className="h-4 w-4" aria-hidden="true" />
                </IconButton>
              </div>
            )
            })}
          </div>
          {selectedPlans.length === 2 ? (
            <div className="flex justify-end border-t border-border/60 pt-3">
              <Button type="button" variant="primary" size="sm" onClick={() => onCompareSelected()}>
                Сравнить планы
              </Button>
            </div>
          ) : null}
        </>
      )}
      <ConfirmDialog
        open={pendingPlan != null}
        onOpenChange={open => {
          if (!open) {
            setPendingPlanId(null)
          }
        }}
        onConfirm={() => {
          if (!pendingPlan) return
          onDeletePlan(pendingPlan.id)
          setPendingPlanId(null)
        }}
        title={pendingPlan ? `Удалить план «${pendingPlan.title}»?` : 'Удалить план?'}
        description="План будет удалён без возможности восстановления. Это не повлияет на опубликованные копии у клиентов."
        confirmLabel="Удалить"
        cancelLabel="Отмена"
        tone="destructive"
        loading={Boolean(isDeleting && deletingPlanId === pendingPlan?.id)}
      />
    </Card>
  )
}

export default PlanListCard
