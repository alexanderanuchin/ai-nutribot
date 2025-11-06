import { FlameKindlingIcon, PieChartIcon } from 'lucide-react'
import clsx from 'clsx'

import { Badge, Card, Skeleton } from '../../../components/ui'
import type { MealPlan, MealPlanDailyTotals } from '../../../types/meal-plan'
import { computeCoverage, extractPlanTargets, formatNutritionValue } from '../utils'

interface PlanSummaryCardProps {
  plan?: MealPlan | null
  isLoading?: boolean
}

function MacroProgressBar({
  label,
  value,
  target,
  colorClass,
}: {
  label: string
  value: number
  target: number
  colorClass: string
}) {
  const percentage = target ? Math.min(100, Math.round((value / target) * 100)) : 0
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>
          {formatNutritionValue(value, 1)} / {formatNutritionValue(target, 1)} г
        </span>
      </div>
      <div className="relative h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={clsx('absolute inset-y-0 left-0 rounded-full transition-all', colorClass)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function DailyNutritionRow({ day }: { day: MealPlanDailyTotals }) {
  const title = day.date ? new Date(day.date).toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric' }) : 'Без даты'
  return (
    <div className="flex items-center justify-between rounded-xl border border-border/60 bg-card/70 px-3 py-2 text-xs text-muted-foreground">
      <div className="flex items-center gap-2">
        <Badge variant={day.is_unscheduled ? 'secondary' : 'outline'} className="uppercase tracking-wide">
          {title}
        </Badge>
      </div>
      <div className="flex items-center gap-3">
        <span>{formatNutritionValue(day.totals.calories, 0)} ккал</span>
        <span>Б {formatNutritionValue(day.totals.protein_g, 1)}</span>
        <span>Ж {formatNutritionValue(day.totals.fat_g, 1)}</span>
        <span>У {formatNutritionValue(day.totals.carbs_g, 1)}</span>
      </div>
    </div>
  )
}

export function PlanSummaryCard({ plan, isLoading = false }: PlanSummaryCardProps) {
  const targets = extractPlanTargets(plan)
  const totals = plan?.nutrition_totals ?? targets
  const coverage = computeCoverage(totals, targets)

  if (isLoading) {
    return (
      <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-16 w-full" />
      </Card>
    )
  }

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-muted-foreground">Баланс нутриентов</div>
          <div className="flex items-center gap-2 text-2xl font-bold text-foreground">
            {formatNutritionValue(totals.calories, 0)}
            <span className="text-base font-medium text-muted-foreground">ккал / день</span>
          </div>
        </div>
        <Badge variant="outline" className="gap-1 text-xs">
          <FlameKindlingIcon className="h-4 w-4" />
          {Math.round(coverage.calories)}%
        </Badge>
      </div>

      <div className="space-y-2">
        <MacroProgressBar label="Белки" value={totals.protein_g} target={targets.protein_g} colorClass="bg-emerald-500" />
        <MacroProgressBar label="Жиры" value={totals.fat_g} target={targets.fat_g} colorClass="bg-amber-500" />
        <MacroProgressBar label="Углеводы" value={totals.carbs_g} target={targets.carbs_g} colorClass="bg-sky-500" />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <PieChartIcon className="h-4 w-4" /> Распределение по дням
        </div>
        <div className="space-y-2">
          {(plan?.daily_breakdown ?? []).map(day => (
            <DailyNutritionRow key={`${day.date ?? 'unscheduled'}`} day={day} />
          ))}
          {(!plan || plan.daily_breakdown.length === 0) && (
            <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
              Добавьте блюда в календарь, чтобы увидеть динамику по дням.
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

export default PlanSummaryCard
