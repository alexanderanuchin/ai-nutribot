import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Clock3Icon, FlameIcon, SparklesIcon } from 'lucide-react'

import type { MarketRecipe } from '../../../types/market'
import { submitPlanItem } from '../plan/api'
import { createPlanSubmissionPayload } from '../plan/form'
import { selectPlanItem, useMarketPlanStore } from '../stores/planStore'
import {
  Badge,
  Button,
  Card,
  QuantityStepper,
  Rating,
  useToast,
} from '../../../components/ui'

export interface RecipeCardProps {
  item: MarketRecipe
}

function formatMinutes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return 'до 10 мин'
  if (value < 60) return `${Math.round(value)} мин`
  const hours = Math.floor(value / 60)
  const minutes = Math.round(value % 60)
  if (minutes === 0) return `${hours} ч`
  return `${hours} ч ${minutes} мин`
}

function formatCalories(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return `${Math.round(value)} ккал`
}

export function RecipeCard({ item }: RecipeCardProps) {
  const hydrated = useMarketPlanStore(state => state.hydrated)
  const upsertItem = useMarketPlanStore(state => state.upsertItem)
  const removeItem = useMarketPlanStore(state => state.removeItem)
  const planItem = useMarketPlanStore(selectPlanItem(item.id))
  const [imageFailed, setImageFailed] = useState(false)
  const { notify } = useToast()

  const servings = planItem?.servings ?? 1
  const inPlan = hydrated && Boolean(planItem)

  const previewImage = useMemo(() => {
    if (imageFailed) return null
    return item.preview_image_url || item.hero_image_url || null
  }, [imageFailed, item.hero_image_url, item.preview_image_url])

  const mutation = useMutation({
    mutationFn: async (nextServings: number) => {
      const submission = createPlanSubmissionPayload({
        recipe_id: item.id,
        servings: Math.max(nextServings, 0),
      })
      return submitPlanItem(submission)
    },
    onSuccess: response => {
      const updatedServings = response.item?.servings ?? 0
      if (response.status === 'removed' || updatedServings <= 0) {
        removeItem(item.id)
        notify({ title: 'Удалено из плана', description: item.title, tone: 'warning' })
        return
      }
      upsertItem({
        id: item.id,
        title: item.title,
        servings: updatedServings,
        calories: item.calories,
        cookTimeMinutes: item.cook_time_minutes,
        imageUrl: item.preview_image_url || item.hero_image_url || null,
        tags: item.tags ?? null,
      })
      notify({ title: 'В плане питания', description: `${item.title} · ${updatedServings} порций`, tone: 'success' })
    },
  })

  const macros = useMemo(
    () => [
      { label: 'Б', value: Math.round(item.protein_g) },
      { label: 'Ж', value: Math.round(item.fat_g) },
      { label: 'У', value: Math.round(item.carbs_g) },
    ],
    [item.carbs_g, item.fat_g, item.protein_g],
  )

  const handleTogglePlan = () => {
    if (!hydrated) return
    mutation.mutate(inPlan ? 0 : servings > 0 ? servings : 1)
  }

  const handleServingsChange = (next: number) => {
    if (!hydrated) return
    mutation.mutate(next)
  }

  return (
    <Card interactive elevation={2} className="flex h-full flex-col gap-4 p-0">
      <div className="relative overflow-hidden rounded-t-2xl">
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted/20">
          {previewImage ? (
            <img
              src={previewImage}
              alt={item.title}
              loading="lazy"
              className="h-full w-full object-cover"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center gap-2 text-sm text-muted-foreground">
              <SparklesIcon className="h-5 w-5" aria-hidden="true" />
              <span>AI рецепт</span>
            </div>
          )}
        </div>
        <div className="absolute inset-x-0 top-3 flex items-center justify-between px-3">
          {item.is_premium ? <Badge tone="primary">Premium</Badge> : null}
          {inPlan ? <Badge tone="success">В плане</Badge> : null}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-4 px-5 pb-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="text-title font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
            {item.subtitle ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.subtitle}</p> : null}
          </div>
          {item.rating ? <Rating value={item.rating} count={item.rating_count ?? undefined} size="sm" /> : null}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/30 px-2 py-1">
            <Clock3Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {formatMinutes(item.cook_time_minutes)}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/30 px-2 py-1">
            <FlameIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {formatCalories(item.calories)}
          </span>
          {item.tags?.slice(0, 3).map(tag => (
            <span key={tag} className="rounded-full bg-muted/20 px-2 py-1 text-[11px] font-medium uppercase tracking-[0.2em]">
              {tag}
            </span>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {macros.map(macro => (
            <div key={macro.label} className="flex flex-col rounded-xl bg-muted/15 px-2 py-2">
              <span className="text-[11px] font-semibold uppercase tracking-[0.3em] text-muted-foreground">{macro.label}</span>
              <span className="text-sm font-semibold text-foreground">{macro.value} г</span>
            </div>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-3">
          {item.price ? (
            <div className="text-sm font-semibold text-primary">
              {item.price.toLocaleString('ru-RU', { style: 'currency', currency: item.currency || 'RUB' })}
            </div>
          ) : (
            <div className="text-sm font-semibold text-success">Бесплатно</div>
          )}
          {inPlan ? (
            <QuantityStepper value={servings} min={1} onChange={handleServingsChange} disabled={mutation.isPending} />
          ) : (
            <Button variant="primary" size="sm" onClick={handleTogglePlan} disabled={!hydrated || mutation.isPending}>
              Добавить
            </Button>
          )}
        </div>
        {inPlan ? (
          <Button variant="ghost" size="sm" onClick={() => handleServingsChange(0)} disabled={mutation.isPending}>
            Удалить из плана
          </Button>
        ) : null}
      </div>
    </Card>
  )
}

export default RecipeCard