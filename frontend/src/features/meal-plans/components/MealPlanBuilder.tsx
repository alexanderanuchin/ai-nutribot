import { useEffect, useMemo, useState } from 'react'
import {
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  closestCenter,
  type DragEndEvent,
  type DragStartEvent,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { addDays, addWeeks, format, startOfWeek, subWeeks } from 'date-fns'
import { ru } from 'date-fns/locale'
import { ArrowLeft, ArrowRight, GlobeIcon, LockIcon } from 'lucide-react'

import { Badge, Button, Card, IconButton, Skeleton, useToast } from '../../../components/ui'
import { DEFAULT_WEEK_DAYS } from '../constants'
import { extractPlanTargets } from '../utils'
import { PlanSlot } from '../types'
import MealPlanCalendar from './MealPlanCalendar'
import PlanGoalsCard from './PlanGoalsCard'
import PlanListCard from './PlanListCard'
import PlanSummaryCard from './PlanSummaryCard'
import RecipeLibrary from './RecipeLibrary'
import {
  useCreateMealPlanItemMutation,
  useCreateMealPlanMutation,
  useDeleteMealPlanItemMutation,
  useDeleteMealPlanMutation,
  useMealPlanQuery,
  useMealPlansQuery,
  useUpdateMealPlanItemMutation,
  useUpdateMealPlanMutation,
} from '../hooks'
import type { MealPlanItemPayload } from '../../../types/meal-plan'

interface ActiveDragState {
  type: 'recipe' | 'product' | 'plan-item'
  recipeId?: number
  productId?: number
  itemId?: number
}

const DEFAULT_TARGETS = {
  calories: 2000,
  protein_g: 120,
  fat_g: 60,
  carbs_g: 220,
}

function buildSlot(date: string | null, mealType: string | null): PlanSlot {
  return { date, mealType: mealType as PlanSlot['mealType'] }
}

export function MealPlanBuilder() {
  const { notify } = useToast()
  const params = useMemo(() => ({ scope: 'owned' as const, page_size: 50 }), [])
  const plansQuery = useMealPlansQuery(params, { keepPreviousData: true })
  const plans = plansQuery.data?.results ?? []

  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const [activeSlot, setActiveSlot] = useState<PlanSlot | null>(null)
  const [activeDrag, setActiveDrag] = useState<ActiveDragState | null>(null)

  useEffect(() => {
    if (plans.length === 0) {
      setSelectedPlanId(null)
      return
    }
    if (selectedPlanId == null) {
      setSelectedPlanId(plans[0].id)
      return
    }
    if (!plans.some(plan => plan.id === selectedPlanId)) {
      setSelectedPlanId(plans[0].id)
    }
  }, [plans, selectedPlanId])

  const planQuery = useMealPlanQuery(selectedPlanId, {
    enabled: Boolean(selectedPlanId),
  })
  const plan = planQuery.data

  const [titleDraft, setTitleDraft] = useState('')
  const [priceDraft, setPriceDraft] = useState('')

  useEffect(() => {
    if (!plan) {
      setTitleDraft('')
      setPriceDraft('')
      return
    }
    const alignedWeek = startOfWeek(new Date(plan.start_date), { weekStartsOn: 1 })
    setWeekStart(alignedWeek)
    if (!activeSlot) {
      setActiveSlot({ date: plan.start_date, mealType: 'breakfast' })
    }
    setTitleDraft(plan.title)
    setPriceDraft(plan.price_amount ?? '')
  }, [plan?.id])

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 10 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 120, tolerance: 8 } }),
    useSensor(KeyboardSensor)
  )

  const createPlanMutation = useCreateMealPlanMutation({
    onSuccess: created => {
      notify({ title: 'План создан', description: 'Вы можете настроить расписание и цели.', tone: 'success' })
      setSelectedPlanId(created.id)
      setActiveSlot({ date: created.start_date, mealType: 'breakfast' })
    },
  })

  const updatePlanMutation = useUpdateMealPlanMutation(selectedPlanId ?? 0)
  const deletePlanMutation = useDeleteMealPlanMutation({
    onSuccess: () => {
      notify({ title: 'План удалён', tone: 'success' })
    },
  })

  const createItemMutation = useCreateMealPlanItemMutation()
  const updateItemMutation = useUpdateMealPlanItemMutation(selectedPlanId ?? 0)
  const deleteItemMutation = useDeleteMealPlanItemMutation(selectedPlanId ?? 0)

  const displayedItems = useMemo(() => {
    if (!plan) return []
    const end = addDays(weekStart, DEFAULT_WEEK_DAYS - 1)
    return plan.items.filter(item => {
      if (!item.scheduled_for) return true
      const scheduled = new Date(item.scheduled_for)
      return scheduled >= weekStart && scheduled <= end
    })
  }, [plan, weekStart])

  const handleCreatePlan = () => {
    const today = format(weekStart, 'yyyy-MM-dd')
    createPlanMutation.mutate({
      title: `План ${new Date().toLocaleDateString('ru-RU')}`,
      start_date: today,
      metadata: { targets: DEFAULT_TARGETS },
    })
  }

  const handleDeletePlan = (planId: number) => {
    deletePlanMutation.mutate(planId)
  }

  const handleUpdateTargets = (targets: typeof DEFAULT_TARGETS) => {
    if (!plan) return
    updatePlanMutation.mutate({ metadata: { ...plan.metadata, targets } })
  }

  const handleTitleCommit = () => {
    if (!plan) return
    const normalized = titleDraft.trim()
    if (!normalized) {
      setTitleDraft(plan.title)
      return
    }
    if (normalized === plan.title) {
      return
    }
    updatePlanMutation.mutate({ title: normalized })
  }

  const handlePriceCommit = () => {
    if (!plan) return
    const numeric = priceDraft.trim() === '' ? null : Number(priceDraft)
    if (numeric !== null && !Number.isFinite(numeric)) {
      notify({ title: 'Некорректная цена', description: 'Введите число или оставьте поле пустым', tone: 'destructive' })
      return
    }
    updatePlanMutation.mutate({ price_amount: numeric, price_currency: plan.price_currency || 'RUB' })
  }

  const handleTogglePublish = () => {
    if (!plan) return
    updatePlanMutation.mutate({ is_published: !plan.is_published })
  }

  const handleWeekShift = (direction: 'prev' | 'next') => {
    setWeekStart(prev => (direction === 'prev' ? subWeeks(prev, 1) : addWeeks(prev, 1)))
  }

  const handleAddLibraryItem = (item: { recipeId?: number; productId?: number }) => {
    if (!plan) {
      notify({
        title: 'Выберите план',
        description: 'Создайте или откройте план, чтобы добавлять элементы',
        tone: 'destructive',
      })
      return
    }
    if (!activeSlot) {
      notify({
        title: 'Выберите ячейку',
        description: 'Нажмите на ячейку календаря перед добавлением элемента',
        tone: 'warning',
      })
      return
    }
    if (!item.recipeId && !item.productId) {
      return
    }
    const payload: MealPlanItemPayload = {
      meal_plan: plan.id,
      servings: 1,
      scheduled_for: activeSlot.date ?? undefined,
      meal_type: activeSlot.mealType ?? undefined,
    }
    if (item.recipeId) {
      payload.recipe = item.recipeId
    }
    if (item.productId) {
      payload.product = item.productId
    }
    createItemMutation.mutate({
      ...payload,
    })
  }

  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current
    if (!data) return
    if (data.type === 'recipe') {
      setActiveDrag({ type: 'recipe', recipeId: data.recipeId })
    } else if (data.type === 'product') {
      setActiveDrag({ type: 'product', productId: data.productId })
    } else if (data.type === 'plan-item') {
      setActiveDrag({ type: 'plan-item', itemId: data.itemId })
    }
  }

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDrag(null)
    const { active, over } = event
    if (!over) return
    const droppable = over.data.current as PlanSlot | undefined
    if (!droppable) return
    const data = active.data.current as ActiveDragState | undefined
    if (!data) return
    if (!plan) return

    if (data.type === 'recipe' && data.recipeId) {
      createItemMutation.mutate({
        meal_plan: plan.id,
        recipe: data.recipeId,
        servings: 1,
        scheduled_for: droppable.date ?? undefined,
        meal_type: droppable.mealType ?? undefined,
      })
      return
    }
    if (data.type === 'product' && data.productId) {
      createItemMutation.mutate({
        meal_plan: plan.id,
        product: data.productId,
        servings: 1,
        scheduled_for: droppable.date ?? undefined,
        meal_type: droppable.mealType ?? undefined,
      })
      return
    }
    if (data.type === 'plan-item' && data.itemId) {
      const payload: MealPlanItemPayload = {
        meal_plan: plan.id,
        scheduled_for: droppable.date ?? undefined,
        meal_type: droppable.mealType ?? undefined,
      }
      updateItemMutation.mutate({ itemId: data.itemId, payload })
    }
  }

  const handleChangeServings = (itemId: number, servings: number) => {
    if (!plan) return
    updateItemMutation.mutate({
      itemId,
      payload: { meal_plan: plan.id, servings },
    })
  }

  const handleRemoveItem = (itemId: number) => {
    deleteItemMutation.mutate(itemId)
  }

  const targets = extractPlanTargets(plan)

  return (
    <div className="flex flex-col gap-6">
      <Card className="space-y-4 border-border/70 bg-background/70 p-5 shadow-level-2">
        {planQuery.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-1/2" />
            <Skeleton className="h-5 w-1/3" />
          </div>
        ) : plan ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <input
                  className="min-w-[12rem] rounded-2xl border border-border/60 bg-card/80 px-4 py-2 text-lg font-semibold text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                  value={titleDraft}
                  onChange={event => setTitleDraft(event.target.value)}
                  onBlur={handleTitleCommit}
                />
                <Badge variant={plan.is_published ? 'outline' : 'secondary'} className="gap-1 text-xs uppercase">
                  {plan.is_published ? <GlobeIcon className="h-4 w-4" aria-hidden="true" /> : <LockIcon className="h-4 w-4" aria-hidden="true" />}
                  {plan.is_published ? 'Опубликован' : 'Черновик'}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  Цена, ₽
                  <input
                    className="w-24 rounded-xl border border-border/60 bg-card/80 px-3 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                    type="number"
                    min={0}
                    step={10}
                    value={priceDraft}
                    onChange={event => setPriceDraft(event.target.value)}
                    onBlur={handlePriceCommit}
                  />
                </label>
                <Button variant={plan.is_published ? 'outline' : 'primary'} size="sm" onClick={handleTogglePublish}>
                  {plan.is_published ? 'Сделать черновиком' : 'Опубликовать'}
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-muted-foreground">
                Неделя начинается {format(weekStart, 'd MMMM', { locale: ru })}
              </div>
              <div className="flex items-center gap-2">
                <IconButton variant="ghost" onClick={() => handleWeekShift('prev')} aria-label="Предыдущая неделя">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                </IconButton>
                <IconButton variant="ghost" onClick={() => handleWeekShift('next')} aria-label="Следующая неделя">
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </IconButton>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">Создайте план, чтобы начать настройку питания.</div>
        )}
      </Card>

      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <div className="space-y-6">
          <PlanSummaryCard plan={plan} isLoading={planQuery.isLoading} />
          <PlanGoalsCard plan={plan} isSaving={updatePlanMutation.isPending} onSave={handleUpdateTargets} />
          <PlanListCard
            plans={plans}
            selectedPlanId={selectedPlanId}
            onSelectPlan={setSelectedPlanId}
            onCreatePlan={handleCreatePlan}
            onDeletePlan={handleDeletePlan}
            isLoading={plansQuery.isLoading}
            isCreating={createPlanMutation.isPending}
            deletingPlanId={deletePlanMutation.variables ?? null}
            isDeleting={deletePlanMutation.isPending}
          />
        </div>
        <div className="flex flex-col gap-6">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <MealPlanCalendar
              weekStart={weekStart}
              daysCount={DEFAULT_WEEK_DAYS}
              items={displayedItems}
              activeSlot={activeSlot}
              onSelectSlot={slot => setActiveSlot(slot)}
              onAddRequest={slot => {
                setActiveSlot(slot)
              }}
              onChangeServings={handleChangeServings}
              onRemoveItem={handleRemoveItem}
            />
          </DndContext>
          <RecipeLibrary activeSlot={activeSlot} onAddItem={handleAddLibraryItem} />
        </div>
      </div>
    </div>
  )
}

export default MealPlanBuilder
