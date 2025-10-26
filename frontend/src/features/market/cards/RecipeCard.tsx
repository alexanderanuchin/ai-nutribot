import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckIcon, Clock3Icon, FlameIcon, Loader2Icon, SparklesIcon } from 'lucide-react'
import clsx from 'clsx'

import type { MarketRecipe } from '../../../types/market'
import { addRecipeToPlan } from '../../../api/market'
import { selectPlanItem, useMarketPlanStore } from '../stores/planStore'

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

  const servings = planItem?.servings ?? 1
  const inPlan = hydrated && Boolean(planItem)

  const previewImage = useMemo(() => {
    if (imageFailed) return null
    return item.preview_image_url || item.hero_image_url || null
  }, [imageFailed, item.hero_image_url, item.preview_image_url])

  const mutation = useMutation({
    mutationFn: async (action: 'add' | 'remove') => {
      if (action === 'remove') {
        await addRecipeToPlan({ recipe_id: item.id, servings: 0 })
        removeItem(item.id)
        return 'removed' as const
      }
      await addRecipeToPlan({ recipe_id: item.id, servings })
      upsertItem({
        id: item.id,
        title: item.title,
        servings,
        calories: item.calories,
        cookTimeMinutes: item.cook_time_minutes,
        imageUrl: item.preview_image_url || item.hero_image_url || null,
        tags: item.tags ?? null,
      })
      return 'added' as const
    },
  })

  const handleTogglePlan = () => {
    if (!hydrated) return
    if (inPlan) {
      mutation.mutate('remove')
    } else {
      mutation.mutate('add')
    }
  }

  const macros = useMemo(
    () => [
      { label: 'Б', value: Math.round(item.protein_g) },
      { label: 'Ж', value: Math.round(item.fat_g) },
      { label: 'У', value: Math.round(item.carbs_g) },
    ],
    [item.carbs_g, item.fat_g, item.protein_g]
  )

  return (
    <article className="flex flex-col overflow-hidden rounded-3xl border border-border/60 bg-background/95 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted/30">
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
        {item.is_premium ? (
          <span className="absolute left-3 top-3 inline-flex items-center rounded-full bg-primary px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary-foreground">
            Premium
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="text-lg font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
            {item.subtitle ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.subtitle}</p> : null}
          </div>
          {item.rating ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-600">
              ★ {item.rating.toFixed(1)}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/50 px-2 py-1">
            <Clock3Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {formatMinutes(item.cook_time_minutes)}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/50 px-2 py-1">
            <FlameIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {formatCalories(item.calories)}
          </span>
          {item.tags?.slice(0, 2).map(tag => (
            <span key={tag} className="rounded-full bg-muted/40 px-2 py-1 text-[11px] font-medium uppercase tracking-wide">
              {tag}
            </span>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {macros.map(macro => (
            <div key={macro.label} className="flex flex-col rounded-xl bg-muted/30 px-2 py-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{macro.label}</span>
              <span className="text-sm font-semibold text-foreground">{macro.value} г</span>
            </div>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-2">
          {item.price ? (
            <div className="text-sm font-semibold text-primary">
              {item.price.toLocaleString('ru-RU', { style: 'currency', currency: item.currency || 'RUB' })}
            </div>
          ) : (
            <div className="text-sm font-semibold text-emerald-600">Бесплатно</div>
          )}
          <button
            type="button"
            onClick={handleTogglePlan}
            disabled={!hydrated || mutation.isPending}
            className={clsx(
              'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              inPlan
                ? 'bg-primary text-primary-foreground shadow-soft'
                : 'bg-muted/60 text-foreground hover:bg-muted'
            )}
          >
            {mutation.isPending ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckIcon className="h-4 w-4" aria-hidden="true" />}
            {inPlan ? 'В плане' : 'Добавить'}
          </button>
        </div>
      </div>
    </article>
  )
}

export default RecipeCard