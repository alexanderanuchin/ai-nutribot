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

import {
  Badge,
  Button,
  Card,
  IconButton,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from '../../../components/ui'
import { DEFAULT_WEEK_DAYS } from '../constants'
import { PlanSlot } from '../types'
import MealPlanCalendar from './MealPlanCalendar'
import PlanGoalsCard from './PlanGoalsCard'
import PlanListCard from './PlanListCard'
import PlanSummaryCard from './PlanSummaryCard'
import ComparisonModal from './ComparisonModal'
import RecipeLibrary from './RecipeLibrary'
import PlanDescriptionCard from './PlanDescriptionCard'
import PlanDescriptionEditor from './PlanDescriptionEditor'
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
import type { Goal } from '../../../types'
import { useAuthContext } from '../../../providers/AuthProvider'
import { useMediaQuery } from '../../../hooks/useMediaQuery'
import { recommendTargetsForGoal } from '../goals'
import { exportMealPlan } from '../api'
import {
  parsePlanDescription,
  type MealPlanExportFormat,
  type PlanDescriptionSchema,
} from '../planDescription'

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

type WorkspaceTab = 'schedule' | 'library'

export function MealPlanBuilder() {
  const { notify } = useToast()
  const { profile } = useAuthContext()
  const params = useMemo(() => ({ scope: 'owned' as const, page_size: 50 }), [])
  const plansQuery = useMealPlansQuery(params, { keepPreviousData: true })
  const plans = plansQuery.data?.results ?? []

  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null)
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const [activeSlot, setActiveSlot] = useState<PlanSlot | null>(null)
  const [activeDrag, setActiveDrag] = useState<ActiveDragState | null>(null)
  const [comparisonSelection, setComparisonSelection] = useState<number[]>([])
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [descriptionOpen, setDescriptionOpen] = useState(false)
  const [exportingFormat, setExportingFormat] = useState<MealPlanExportFormat | null>(null)
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>('schedule')

  useEffect(() => {
    if (plans.length === 0) {
      setSelectedPlanId(null)
      setComparisonSelection([])
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

  useEffect(() => {
    setComparisonSelection(prev => prev.filter(id => plans.some(plan => plan.id === id)))
  }, [plans])

  const planQuery = useMealPlanQuery(selectedPlanId, {
    enabled: Boolean(selectedPlanId),
  })
  const plan = planQuery.data

  const [titleDraft, setTitleDraft] = useState('')
  const [priceDraft, setPriceDraft] = useState('')

  const parsedDescription = useMemo(() => {
    if (!plan) return null
    return parsePlanDescription(plan.description)
  }, [plan?.id, plan?.description])

  const hasDescriptionContent = useMemo(() => {
    if (!parsedDescription) return false
    const { sections } = parsedDescription
    if (sections.followUpRequirements.length > 0) {
      return true
    }
    return [
      sections.interventionGoal,
      sections.rationale,
      sections.dietaryPrinciples,
      sections.clientRecommendations,
      sections.monitoringPlan,
    ].some(value => Boolean(value && value.trim()))
  }, [parsedDescription])

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

  const defaultGoal = (profile?.goal as Goal | undefined) ?? 'maintain'
  const recommendedDefaults = recommendTargetsForGoal({ goal: defaultGoal, profile, fallback: DEFAULT_TARGETS })

  const handleCreatePlan = () => {
    const today = format(weekStart, 'yyyy-MM-dd')
    createPlanMutation.mutate({
      title: `План ${new Date().toLocaleDateString('ru-RU')}`,
      start_date: today,
      metadata: { goal: defaultGoal, targets: recommendedDefaults },
    })
  }

  const handleDeletePlan = (planId: number) => {
    setComparisonSelection(prev => prev.filter(id => id !== planId))
    deletePlanMutation.mutate(planId)
  }

  const handleTogglePlanComparison = (planId: number) => {
    setComparisonSelection(prev => {
      if (prev.includes(planId)) {
        return prev.filter(id => id !== planId)
      }
      if (prev.length >= 2) {
        notify({
          title: 'Сравнение максимум двух планов',
          description: 'Снимите отметку, чтобы выбрать другой план',
          tone: 'warning',
        })
        return prev
      }
      return [...prev, planId]
    })
  }

  const handleCompareSelectedPlans = () => {
    if (comparisonSelection.length === 2) {
      setComparisonOpen(true)
    }
  }

  const handleComparisonOpenChange = (open: boolean) => {
    setComparisonOpen(open)
    if (!open) {
      setComparisonSelection([])
    }
  }

  const handleUpdateTargets = ({ goal, targets }: { goal: Goal; targets: typeof DEFAULT_TARGETS }) => {
    if (!plan) return
    updatePlanMutation.mutate({ metadata: { ...plan.metadata, goal, targets } })
  }

  const handleSaveDescription = (nextSchema: PlanDescriptionSchema, serialized: string) => {
    if (!plan) {
      notify({
        title: 'Выберите план',
        description: 'Откройте или создайте план перед сохранением описания.',
        tone: 'warning',
      })
      return
    }
    const nextMetadata: Record<string, unknown> = { ...(plan.metadata ?? {}) }
    if (nextSchema.sections.nextReviewDate) {
      nextMetadata.review = {
        next_review_date: nextSchema.sections.nextReviewDate,
        template_slug: nextSchema.templateSlug ?? null,
      }
    } else if ('review' in nextMetadata) {
      delete nextMetadata.review
    }
    updatePlanMutation.mutate(
      { description: serialized, metadata: nextMetadata },
      {
        onSuccess: () => {
          notify({
            title: 'Описание обновлено',
            description: 'Структура вмешательства сохранена для экспорта и мониторинга.',
            tone: 'success',
          })
          setDescriptionOpen(false)
        },
        onError: error => {
          const message = error instanceof Error ? error.message : 'Не удалось сохранить описание.'
          notify({
            title: 'Ошибка сохранения',
            description: message,
            tone: 'destructive',
          })
        },
      },
    )
  }

  const handleExportPlan = async (format: MealPlanExportFormat) => {
    if (!plan) {
      notify({
        title: 'Выберите план',
        description: 'Создайте или откройте план, чтобы экспортировать файлы.',
        tone: 'warning',
      })
      return
    }
    setExportingFormat(format)
    try {
      const { blob, filename } = await exportMealPlan(plan.id, format)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      notify({
        title: 'Экспорт готов',
        description: `Файл ${filename} сохранён`,
        tone: 'success',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Попробуйте ещё раз позже.'
      notify({
        title: 'Экспорт не выполнен',
        description: message,
        tone: 'destructive',
      })
    } finally {
      setExportingFormat(null)
    }
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

  const isDesktop = useMediaQuery('(min-width: 1280px)')

  const plannerWorkspace = (
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
  )

  const libraryWorkspace = <RecipeLibrary activeSlot={activeSlot} onAddItem={handleAddLibraryItem} />

  return (
    <>
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
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    leadingIcon={<span aria-hidden="true">🖉</span>}
                    onClick={() => setDescriptionOpen(true)}
                  >
                    {hasDescriptionContent ? 'Править описание' : 'Добавить описание'}
                  </Button>
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
            <PlanDescriptionCard
              plan={plan}
              onEdit={() => setDescriptionOpen(true)}
              onExport={handleExportPlan}
              isExporting={exportingFormat}
            />
            <PlanSummaryCard plan={plan} isLoading={planQuery.isLoading} />
            <PlanGoalsCard
              plan={plan}
              profile={profile}
              isSaving={updatePlanMutation.isPending}
              onSave={handleUpdateTargets}
            />
            <PlanListCard
              plans={plans}
              selectedPlanId={selectedPlanId}
              onSelectPlan={setSelectedPlanId}
              onCreatePlan={handleCreatePlan}
              onDeletePlan={handleDeletePlan}
              selectedPlans={comparisonSelection}
              onToggleSelectPlan={handleTogglePlanComparison}
              onCompareSelected={handleCompareSelectedPlans}
              isLoading={plansQuery.isLoading}
              isCreating={createPlanMutation.isPending}
              deletingPlanId={deletePlanMutation.variables ?? null}
              isDeleting={deletePlanMutation.isPending}
            />
          </div>
          <div className="flex flex-col gap-6">
            {isDesktop ? (
              <>
                {plannerWorkspace}
                {libraryWorkspace}
              </>
            ) : (
              <div className="space-y-4">
                <Tabs
                  value={workspaceTab}
                  onValueChange={value => {
                    if (value === 'schedule' || value === 'library') {
                      setWorkspaceTab(value)
                    }
                  }}
                >
                  <TabsList className="border-none bg-transparent p-0">
                    <TabsTrigger value="schedule" className="flex-1">
                      Календарь
                    </TabsTrigger>
                    <TabsTrigger value="library" className="flex-1">
                      Библиотека
                    </TabsTrigger>
                  </TabsList>
                  <TabsContent
                    value="schedule"
                    forceMount
                    className="border-none bg-transparent p-0 shadow-none"
                  >
                    <div className="flex flex-col gap-4">{plannerWorkspace}</div>
                  </TabsContent>
                  <TabsContent
                    value="library"
                    forceMount
                    className="border-none bg-transparent p-0 shadow-none"
                  >
                    {libraryWorkspace}
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </div>
        </div>
      </div>
      <ComparisonModal
        open={comparisonOpen}
        onOpenChange={handleComparisonOpenChange}
        planIds={comparisonSelection}
      />
      <PlanDescriptionEditor
        plan={plan}
        open={descriptionOpen}
        onOpenChange={setDescriptionOpen}
        onSave={handleSaveDescription}
      />
    </>
  )
}

export default MealPlanBuilder
