import { useEffect, useMemo, useState } from 'react'
import { BarChart3Icon, ChevronDownIcon, FlameKindlingIcon, PieChartIcon } from 'lucide-react'
import clsx from 'clsx'

import { Badge, Button, Card, Skeleton } from '../../../components/ui'
import type { MealPlan, MealPlanDailyTotals } from '../../../types/meal-plan'
import { computeCoverage, extractPlanTargets, formatNutritionValue } from '../utils'
import { PLAN_GOAL_PRESETS, formatCalorieDelta } from '../goals'
import type { Goal } from '../../../types'

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

function CaloriesTrendChart({
  days,
  targetCalories,
}: {
  days: MealPlanDailyTotals[]
  targetCalories: number
}) {
  const chartWidth = 360
  const chartHeight = 200
  const paddingX = 28
  const paddingTop = 16
  const paddingBottom = 42
  const maxCalories = useMemo(() => {
    if (days.length === 0) return targetCalories
    const dayMax = Math.max(...days.map(day => day.totals.calories))
    return Math.max(dayMax, targetCalories)
  }, [days, targetCalories])

  if (!maxCalories) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
        Недостаточно данных, чтобы построить график.
      </div>
    )
  }

  const innerHeight = chartHeight - paddingTop - paddingBottom
  const innerWidth = chartWidth - paddingX * 2
  const scaleY = innerHeight / maxCalories
  const step = innerWidth / days.length
  const barWidth = Math.max(18, step * 0.55)
  const horizontalTicks = 4
  const tickValues = Array.from({ length: horizontalTicks }, (_, index) => ((index + 1) / horizontalTicks) * maxCalories)

  return (
    <div className="space-y-3">
      <div className="relative">
        <svg
          role="img"
          aria-label="График изменения калорий по дням"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="h-48 w-full"
        >
          <defs>
            <linearGradient id="calorie-bar" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="hsl(199 89% 48%)" stopOpacity="0.95" />
              <stop offset="100%" stopColor="hsl(199 89% 48%)" stopOpacity="0.6" />
            </linearGradient>
          </defs>
          {tickValues.map(value => {
            const y = chartHeight - paddingBottom - value * scaleY
            return (
              <g key={`tick-${value.toFixed(2)}`}>
                <line x1={paddingX} x2={chartWidth - paddingX} y1={y} y2={y} className="stroke-muted" strokeDasharray="4 4" strokeWidth={0.6} />
                <text
                  x={paddingX - 6}
                  y={y + 4}
                  className="fill-muted-foreground text-[10px]"
                  textAnchor="end"
                >
                  {Math.round(value).toLocaleString('ru-RU')}
                </text>
              </g>
            )
          })}
          <line
            x1={paddingX}
            x2={chartWidth - paddingX}
            y1={chartHeight - paddingBottom}
            y2={chartHeight - paddingBottom}
            className="stroke-border"
            strokeWidth={1}
          />
          {targetCalories > 0 && (
            <line
              x1={paddingX}
              x2={chartWidth - paddingX}
              y1={chartHeight - paddingBottom - targetCalories * scaleY}
              y2={chartHeight - paddingBottom - targetCalories * scaleY}
              className="stroke-primary"
              strokeDasharray="6 6"
              strokeWidth={1.5}
            />
          )}
          {days.map((day, index) => {
            const calories = day.totals.calories
            const barHeight = calories * scaleY
            const x = paddingX + step * index + (step - barWidth) / 2
            const y = chartHeight - paddingBottom - barHeight
            const date = day.date ? new Date(day.date) : undefined
            const label = date
              ? date.toLocaleDateString('ru-RU', { weekday: 'short' })
              : `Д${index + 1}`
            const tooltipLabel = date
              ? date.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'short' })
              : `Без даты · День ${index + 1}`
            return (
              <g key={day.date ?? `unscheduled-${index}`}>
                <rect
                  x={x}
                  y={Math.min(y, chartHeight - paddingBottom)}
                  width={barWidth}
                  height={Math.max(barHeight, 1)}
                  rx={6}
                  className="fill-[url(#calorie-bar)]"
                >
                  <title>
                    {`${tooltipLabel}: ${Math.round(calories).toLocaleString('ru-RU')} ккал`}
                  </title>
                </rect>
                <text
                  x={x + barWidth / 2}
                  y={chartHeight - paddingBottom + 16}
                  className="fill-muted-foreground text-[11px] uppercase"
                  textAnchor="middle"
                >
                  {label}
                </text>
              </g>
            )
          })}
        </svg>
        {targetCalories > 0 && (
          <span className="absolute right-4 top-4 flex items-center gap-1 rounded-full bg-background/80 px-2 py-1 text-[11px] font-medium text-muted-foreground shadow-sm">
            <span className="h-1 w-6 border border-dashed border-primary" aria-hidden="true" />
            Цель: {formatNutritionValue(targetCalories, 0)} ккал
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-sky-500" aria-hidden="true" />
          Факт
        </div>
        {targetCalories > 0 && (
          <div className="flex items-center gap-2">
            <span className="h-2 w-6 border border-dashed border-primary" aria-hidden="true" />
            Цель
          </div>
        )}
      </div>
    </div>
  )
}

function MacroDistributionChart({
  calories,
  protein,
  fat,
  carbs,
}: {
  calories: number
  protein: number
  fat: number
  carbs: number
}) {
  const proteinCalories = Math.max(0, protein * 4)
  const fatCalories = Math.max(0, fat * 9)
  const carbCalories = Math.max(0, carbs * 4)
  const totalCaloriesFromMacros = proteinCalories + fatCalories + carbCalories

  const chartCalories = totalCaloriesFromMacros || calories

  if (!chartCalories) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
        Добавьте блюда в план, чтобы увидеть распределение БЖУ.
      </div>
    )
  }

  const macros = [
    {
      key: 'protein' as const,
      label: 'Белки',
      calories: proteinCalories,
      grams: protein,
      colorClass: 'bg-emerald-500',
      gradientColor: 'hsl(152 76% 46%)',
    },
    {
      key: 'fat' as const,
      label: 'Жиры',
      calories: fatCalories,
      grams: fat,
      colorClass: 'bg-amber-500',
      gradientColor: 'hsl(38 92% 50%)',
    },
    {
      key: 'carbs' as const,
      label: 'Углеводы',
      calories: carbCalories,
      grams: carbs,
      colorClass: 'bg-sky-500',
      gradientColor: 'hsl(199 89% 48%)',
    },
  ]

  let startAngle = 0
  const gradientSegments: string[] = []
  macros.forEach(segment => {
    const percent = totalCaloriesFromMacros ? (segment.calories / totalCaloriesFromMacros) * 100 : 0
    const angle = percent * 3.6
    const endAngle = startAngle + angle
    gradientSegments.push(`${segment.gradientColor} ${startAngle}deg ${Math.min(endAngle, 360)}deg`)
    startAngle = endAngle
  })
  if (startAngle < 360) {
    gradientSegments.push(`#e5e7eb ${startAngle}deg 360deg`)
  }

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
      <div className="relative mx-auto h-36 w-36 flex-shrink-0 overflow-hidden rounded-full border border-border/60 bg-muted/20 shadow-inner">
        <div
          className="absolute inset-0"
          style={{ backgroundImage: `conic-gradient(${gradientSegments.join(', ')})` }}
        />
        <div className="absolute inset-5 rounded-full bg-background/95 shadow-lg" />
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-[11px] uppercase text-muted-foreground">Ккал</span>
          <span className="text-lg font-semibold text-foreground">
            {formatNutritionValue(chartCalories, 0)}
          </span>
        </div>
      </div>
      <div className="grid w-full gap-2 text-sm">
        {macros.map(macro => {
          const percent = totalCaloriesFromMacros ? Math.round((macro.calories / totalCaloriesFromMacros) * 100) : 0
          return (
            <div
              key={macro.key}
              className="flex items-center justify-between rounded-xl border border-border/60 bg-card/60 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className={clsx('h-2.5 w-2.5 rounded-full', macro.colorClass)} aria-hidden="true" />
                <span className="font-medium text-foreground">{macro.label}</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {formatNutritionValue(macro.grams, 1)} г · {percent}%
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function PlanSummaryCard({ plan, isLoading = false }: PlanSummaryCardProps) {
  const targets = extractPlanTargets(plan)
  const totals = plan?.nutrition_totals ?? targets
  const coverage = computeCoverage(totals, targets)
  const rawGoal = plan?.metadata?.goal
  const planGoal =
    typeof rawGoal === 'string' && rawGoal in PLAN_GOAL_PRESETS ? (rawGoal as Goal) : undefined
  const goalPreset = planGoal ? PLAN_GOAL_PRESETS[planGoal] : undefined
  const dailyBreakdown = plan?.daily_breakdown ?? []
  const hasTrendData = dailyBreakdown.length > 1
  const [showDailyBreakdown, setShowDailyBreakdown] = useState(() => !hasTrendData)

  useEffect(() => {
    setShowDailyBreakdown(!hasTrendData)
  }, [hasTrendData])

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
          {goalPreset && (
            <div className="text-xs text-muted-foreground">
              Цель: {goalPreset.label} ({formatCalorieDelta(goalPreset.calorieMultiplier)})
            </div>
          )}
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

      {hasTrendData && (
        <div className="space-y-3 rounded-2xl border border-border/60 bg-card/50 px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <BarChart3Icon className="h-4 w-4" /> Динамика калорий
            </div>
          </div>
          <CaloriesTrendChart days={dailyBreakdown} targetCalories={targets.calories} />
        </div>
      )}

      <div className="space-y-3 rounded-2xl border border-border/60 bg-card/50 px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <PieChartIcon className="h-4 w-4" /> Распределение БЖУ
          </div>
        </div>
        <MacroDistributionChart
          calories={totals.calories}
          protein={totals.protein_g}
          fat={totals.fat_g}
          carbs={totals.carbs_g}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <span className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4" /> Распределение по дням
          </span>
          {dailyBreakdown.length > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-9 gap-1 rounded-lg px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
              onClick={() => setShowDailyBreakdown(current => !current)}
              aria-expanded={showDailyBreakdown}
            >
              {showDailyBreakdown ? 'Скрыть' : 'Показать'}
              <ChevronDownIcon
                className={clsx('h-4 w-4 transition-transform', showDailyBreakdown ? 'rotate-180' : 'rotate-0')}
                aria-hidden="true"
              />
            </Button>
          )}
        </div>
        {dailyBreakdown.length > 0 ? (
          <div className={clsx('space-y-2', showDailyBreakdown ? 'block' : 'hidden')}>
            {dailyBreakdown.map(day => (
              <DailyNutritionRow key={`${day.date ?? 'unscheduled'}`} day={day} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
            Добавьте блюда в календарь, чтобы увидеть динамику по дням.
          </div>
        )}
      </div>
    </Card>
  )
}

export default PlanSummaryCard
