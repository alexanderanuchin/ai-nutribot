import { useEffect, useState } from 'react'
import { SparklesIcon } from 'lucide-react'

import { Badge, Button, Card } from '../../../components/ui'
import type { MealPlan } from '../../../types/meal-plan'
import { extractPlanTargets } from '../utils'

interface PlanGoalsCardProps {
  plan?: MealPlan | null
  isSaving?: boolean
  onSave: (targets: { calories: number; protein_g: number; fat_g: number; carbs_g: number }) => void
}

interface TargetState {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
}

export function PlanGoalsCard({ plan, isSaving = false, onSave }: PlanGoalsCardProps) {
  const [targets, setTargets] = useState<TargetState>(() => extractPlanTargets(plan))
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    const next = extractPlanTargets(plan)
    setTargets(next)
    setDirty(false)
  }, [plan?.id, JSON.stringify(plan?.metadata?.targets ?? {})])

  const handleChange = (field: keyof TargetState, value: string) => {
    const numeric = Number(value)
    setTargets(prev => ({ ...prev, [field]: Number.isFinite(numeric) ? numeric : 0 }))
    setDirty(true)
  }

  const handleSubmit = () => {
    onSave(targets)
    setDirty(false)
  }

  const inputClass =
    'w-full rounded-xl border border-border/60 bg-card/80 px-3 py-2 text-sm text-foreground shadow-inner transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60'

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-muted-foreground">Цели на день</div>
          <div className="text-foreground">Настройте калорийность и БЖУ</div>
        </div>
        <Badge variant="outline" className="gap-1 text-xs">
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
        <Button variant="primary" size="sm" disabled={!dirty || isSaving} onClick={handleSubmit}>
          Сохранить цели
        </Button>
      </div>
    </Card>
  )
}

export default PlanGoalsCard
