import { useEffect, useMemo, useState, type ChangeEvent } from 'react'
import { SparklesIcon, Wand2Icon } from 'lucide-react'

import { Badge, Button, Card } from '../../../components/ui'
import type { MealPlan } from '../../../types/meal-plan'
import type { Goal, Profile } from '../../../types'
import { extractPlanTargets } from '../utils'
import {
  PLAN_GOAL_PRESETS,
  PLAN_GOAL_OPTIONS,
  formatCalorieDelta,
  getPlanGoalPreset,
  recommendTargetsForGoal,
} from '../goals'

interface PlanGoalsCardProps {
  plan?: MealPlan | null
  isSaving?: boolean
  profile?: Profile
  onSave: (payload: { goal: Goal; targets: { calories: number; protein_g: number; fat_g: number; carbs_g: number } }) => void
}

interface TargetState {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export function PlanGoalsCard({ plan, isSaving = false, profile, onSave }: PlanGoalsCardProps) {
  const [targets, setTargets] = useState<TargetState>(() => extractPlanTargets(plan))
  const [dirty, setDirty] = useState(false)
  const planGoal = (plan?.metadata?.goal as Goal | undefined) ?? undefined
  const defaultGoal = useMemo<Goal>(() => {
    if (planGoal && PLAN_GOAL_PRESETS[planGoal]) return planGoal
    return (profile?.goal as Goal | undefined) ?? 'maintain'
  }, [planGoal, profile?.goal])
  const [selectedGoal, setSelectedGoal] = useState<Goal>(defaultGoal)

  useEffect(() => {
    const next = extractPlanTargets(plan)
    setTargets(next)
    setDirty(false)
  }, [plan?.id, JSON.stringify(plan?.metadata?.targets ?? {})])

  useEffect(() => {
    setSelectedGoal(defaultGoal)
  }, [defaultGoal])

  const handleChange = (field: keyof TargetState, value: string) => {
    const numeric = Number(value)
    setTargets(prev => ({ ...prev, [field]: Number.isFinite(numeric) ? numeric : 0 }))
    setDirty(true)
  }

  const handleApplyRecommendation = (goal: Goal) => {
    const fallbackTotals = targets.calories > 0 ? targets : extractPlanTargets(plan)
    const recommended = recommendTargetsForGoal({ goal, profile, fallback: fallbackTotals })
    setTargets(recommended)
    setDirty(true)
  }

  const handleGoalChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextGoal = (event.target.value as Goal) ?? selectedGoal
    setSelectedGoal(nextGoal)
    handleApplyRecommendation(nextGoal)
  }

  const handleRecommend = () => {
    handleApplyRecommendation(selectedGoal)
  }

  const handleSubmit = () => {
    onSave({ goal: selectedGoal, targets })
    setDirty(false)
  }

  const inputClass =
    'w-full rounded-xl border border-border/60 bg-card/80 px-3 py-2 text-sm text-foreground shadow-inner transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60'
  const goalPreset = getPlanGoalPreset(selectedGoal)
  const hasChanges = dirty || selectedGoal !== planGoal

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="text-sm font-semibold text-muted-foreground">Цели на день</div>
          <div className="text-foreground">Настройте калорийность и БЖУ</div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="font-semibold uppercase tracking-wide">Цель:</span>
            <div className="relative">
              <select
                className="peer w-48 appearance-none rounded-xl border border-border/60 bg-card/80 px-3 py-2 pr-8 text-sm text-foreground shadow-inner transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                value={selectedGoal}
                onChange={handleGoalChange}
              >
                {PLAN_GOAL_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-base text-muted-foreground">
                🠗
              </span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="xs"
              className="gap-1"
              onClick={handleRecommend}
              disabled={isSaving}
            >
              <Wand2Icon className="h-4 w-4" />
              Рекомендовать
            </Button>
          </div>
          <div className="text-xs text-muted-foreground">
            {goalPreset.label}: {goalPreset.description}{' '}
            <span className="font-medium text-foreground">{formatCalorieDelta(goalPreset.calorieMultiplier)}</span> ккал от поддержания
          </div>
        </div>
        <Badge variant="outline" className="ml-auto gap-1 text-xs">
          <SparklesIcon className="h-4 w-4" />
          Без AI
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          Калории, ккал
          <input
            className={inputClass}
            type="number"
            min={0}
            step={10}
            value={targets.calories}
            onChange={event => handleChange('calories', event.target.value)}
          />
        </label>
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          Белки, г
          <input
            className={inputClass}
            type="number"
            min={0}
            step={1}
            value={targets.protein_g}
            onChange={event => handleChange('protein_g', event.target.value)}
          />
        </label>
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          Жиры, г
          <input
            className={inputClass}
            type="number"
            min={0}
            step={1}
            value={targets.fat_g}
            onChange={event => handleChange('fat_g', event.target.value)}
          />
        </label>
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          Углеводы, г
          <input
            className={inputClass}
            type="number"
            min={0}
            step={1}
            value={targets.carbs_g}
            onChange={event => handleChange('carbs_g', event.target.value)}
          />
        </label>
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Эти значения применяются ко всему плану и используются при расчёте прогресса по дням.
        </p>
        <Button variant="primary" size="sm" disabled={!hasChanges || isSaving} onClick={handleSubmit}>
          Сохранить цели
        </Button>
      </div>
    </Card>
  )
}

export default PlanGoalsCard
