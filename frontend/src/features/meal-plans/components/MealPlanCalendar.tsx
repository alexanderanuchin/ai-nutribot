import { useMemo } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { addDays, format, isSameDay } from 'date-fns'
import { ru } from 'date-fns/locale'
import clsx from 'clsx'

import { Button, Card } from '../../../components/ui'
import type { MealPlanItem } from '../../../types/meal-plan'
import MealPlanItemCard from './MealPlanItemCard'
import { MEAL_TYPES } from '../constants'
import type { MealTypeId } from '../../../types/meal-plan'
import type { PlanSlot } from '../types'

interface MealPlanCalendarProps {
  weekStart: Date
  daysCount: number
  items: MealPlanItem[]
  activeSlot: PlanSlot | null
  onSelectSlot: (slot: PlanSlot) => void
  onAddRequest: (slot: PlanSlot) => void
  onChangeServings: (itemId: number, servings: number) => void
  onRemoveItem: (itemId: number) => void
}

function buildSlotKey(dateKey: string | null, mealType: string | null) {
  return `cell:${dateKey ?? 'unscheduled'}:${mealType ?? 'unscheduled'}`
}

function useSlotDroppable(dateKey: string | null, mealType: MealTypeId | null) {
  const id = buildSlotKey(dateKey, mealType)
  return useDroppable({
    id,
    data: {
      date: dateKey,
      mealType,
    },
  })
}

function DayHeader({ dateValue, isActive }: { dateValue: Date; isActive: boolean }) {
  return (
    <div
      className={clsx(
        'relative rounded-2xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-3 text-left shadow-level-1',
        isActive && 'ring-2 ring-primary'
      )}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {format(dateValue, 'EEEE', { locale: ru })}
      </div>
      <div className="text-2xl font-bold text-foreground">{format(dateValue, 'd MMM', { locale: ru })}</div>
    </div>
  )
}

interface CalendarCellProps {
  dateKey: string | null
  mealType: MealTypeId | null
  label: string
  description: string
  items: MealPlanItem[]
  isActive: boolean
  onSelect: () => void
  onAddRequest: () => void
  onChangeServings: (itemId: number, servings: number) => void
  onRemoveItem: (itemId: number) => void
}

function CalendarCell({
  dateKey,
  mealType,
  label,
  description,
  items,
  isActive,
  onSelect,
  onAddRequest,
  onChangeServings,
  onRemoveItem,
}: CalendarCellProps) {
  const { isOver, setNodeRef } = useSlotDroppable(dateKey, mealType)
  return (
    <div
      ref={setNodeRef}
      className={clsx(
        'relative flex min-h-[9rem] flex-col gap-3 rounded-2xl border border-dashed border-border/60 bg-card/90 p-3 backdrop-blur-sm transition',
        isOver && 'border-primary bg-primary/5 shadow-level-2',
        isActive && !isOver && 'border-primary/70'
      )}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-foreground">{label}</div>
          <div className="text-xs text-muted-foreground">{description}</div>
        </div>
        <Button variant="secondary" size="sm" onClick={onAddRequest}>
          Добавить
        </Button>
      </div>
      <div className="flex flex-col gap-3">
        {items.length === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-border/50 bg-muted/20 p-4 text-xs text-muted-foreground">
            Перетащите рецепт или продукт либо нажмите «Добавить»
          </div>
        ) : (
          items.map(item => (
            <MealPlanItemCard
              key={item.id}
              item={item}
              onChangeServings={value => onChangeServings(item.id, value)}
              onRemove={() => onRemoveItem(item.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

export function MealPlanCalendar({
  weekStart,
  daysCount,
  items,
  activeSlot,
  onSelectSlot,
  onAddRequest,
  onChangeServings,
  onRemoveItem,
}: MealPlanCalendarProps) {
  const days = useMemo(() =>
    Array.from({ length: daysCount }, (_, index) => addDays(weekStart, index)),
  [daysCount, weekStart])

  const itemsBySlot = useMemo(() => {
    const map = new Map<string, MealPlanItem[]>()
    items.forEach(item => {
      const key = buildSlotKey(item.scheduled_for ?? null, (item.meal_type as MealTypeId | null) ?? null)
      if (!map.has(key)) {
        map.set(key, [])
      }
      map.get(key)!.push(item)
    })
    return map
  }, [items])

  const unscheduledItems = items.filter(item => !item.scheduled_for)

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 lg:grid-cols-3 xl:grid-cols-4">
        {days.map(day => (
          <Card key={day.toISOString()} className="flex flex-col gap-4 border-border/70 bg-background/60 p-4 shadow-level-1">
            <DayHeader dateValue={day} isActive={Boolean(activeSlot?.date && isSameDay(new Date(activeSlot.date), day))} />
            <div className="flex flex-col gap-3">
              {MEAL_TYPES.map(meal => {
                const dateKey = format(day, 'yyyy-MM-dd')
                const slotKey = buildSlotKey(dateKey, meal.id)
                const slotItems = itemsBySlot.get(slotKey) ?? []
                return (
                  <CalendarCell
                    key={slotKey}
                    dateKey={dateKey}
                    mealType={meal.id}
                    label={meal.label}
                    description={meal.description}
                    items={slotItems}
                    isActive={activeSlot?.date === dateKey && activeSlot?.mealType === meal.id}
                    onSelect={() => onSelectSlot({ date: dateKey, mealType: meal.id })}
                    onAddRequest={() => onAddRequest({ date: dateKey, mealType: meal.id })}
                    onChangeServings={onChangeServings}
                    onRemoveItem={onRemoveItem}
                  />
                )
              })}
            </div>
          </Card>
        ))}
        <Card className="flex flex-col gap-4 border-dashed border-border/60 bg-background/50 p-4 shadow-level-1">
          <div className="text-lg font-semibold text-foreground">Без даты</div>
          <CalendarCell
            dateKey={null}
            mealType={null}
            label="Незапланировано"
            description="Продукты и блюда без даты"
            items={unscheduledItems}
            isActive={!activeSlot?.date}
            onSelect={() => onSelectSlot({ date: null, mealType: null })}
            onAddRequest={() => onAddRequest({ date: null, mealType: null })}
            onChangeServings={onChangeServings}
            onRemoveItem={onRemoveItem}
          />
        </Card>
      </div>
    </div>
  )
}

export default MealPlanCalendar
