import { useMemo } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { GripVerticalIcon, PackageIcon, Trash2Icon, UtensilsCrossedIcon } from 'lucide-react'
import clsx from 'clsx'

import { IconButton, QuantityStepper, Tooltip } from '../../../components/ui'
import type { MealPlanItem } from '../../../types/meal-plan'
import { formatNutritionValue } from '../utils'

interface MealPlanItemCardProps {
  item: MealPlanItem
  onChangeServings: (value: number) => void
  onRemove: () => void
  isDisabled?: boolean
}

export function MealPlanItemCard({ item, onChangeServings, onRemove, isDisabled = false }: MealPlanItemCardProps) {
  const dragId = useMemo(() => `plan-item-${item.id}`, [item.id])
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: dragId,
    data: {
      type: 'plan-item',
      itemId: item.id,
      mealPlanId: item.meal_plan,
      servings: item.servings,
    },
    disabled: isDisabled,
  })

  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.6 : 1,
  }

  const title = item.recipe_snapshot?.title ?? item.product_snapshot?.title ?? 'Элемент плана'
  const isProduct = Boolean(item.product_snapshot)
  const subtitle = item.recipe_snapshot
    ? `${formatNutritionValue(item.recipe_snapshot.calories, 0)} ккал · ${item.recipe_snapshot.cooking_time_minutes} мин`
    : item.product_snapshot
      ? `${formatNutritionValue(item.product_snapshot.calories, 0)} ккал · продукт`
      : null

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={clsx(
        'group relative flex w-full items-start gap-3 rounded-2xl border border-border/60 bg-card/95 p-3 shadow-level-1 transition hover:shadow-level-2',
        isDragging && 'z-30 border-primary/60 shadow-level-3'
      )}
    >
      <button
        type="button"
        className="mt-1 inline-flex h-8 w-8 flex-none items-center justify-center rounded-full bg-muted/50 text-muted-foreground transition hover:bg-muted"
        aria-label="Переместить элемент"
        {...attributes}
        {...listeners}
      >
        <GripVerticalIcon className="h-4 w-4" aria-hidden="true" />
      </button>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-foreground">{title}</div>
            {subtitle ? <div className="truncate text-xs text-muted-foreground">{subtitle}</div> : null}
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-[11px] font-semibold text-muted-foreground">
            {isProduct ? (
              <PackageIcon className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <UtensilsCrossedIcon className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {isProduct ? 'Продукт' : 'Рецепт'}
          </span>
          <Tooltip content="Удалить из плана">
            <IconButton
              aria-label="Удалить элемент"
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              onClick={onRemove}
            >
              <Trash2Icon className="h-4 w-4" aria-hidden="true" />
            </IconButton>
          </Tooltip>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <QuantityStepper
            value={Number(item.servings) || 0}
            min={0.5}
            step={0.5}
            onChange={onChangeServings}
          />
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-muted px-2 py-1 font-medium text-foreground">
              {formatNutritionValue(item.total_nutrition.calories, 0)} ккал
            </span>
            <span>Б {formatNutritionValue(item.total_nutrition.protein_g, 1)} г</span>
            <span>Ж {formatNutritionValue(item.total_nutrition.fat_g, 1)} г</span>
            <span>У {formatNutritionValue(item.total_nutrition.carbs_g, 1)} г</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MealPlanItemCard
