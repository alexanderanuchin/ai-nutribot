import { Link } from 'react-router-dom'
import { CalendarDaysIcon, FlameIcon, LayersIcon, StarIcon, TagsIcon } from 'lucide-react'
import clsx from 'clsx'

import type { MealPlan } from '../../../types/meal-plan'
import { Badge, Card } from '../../../components/ui'

const GOAL_LABELS: Record<string, string> = {
  weight_loss: 'Похудение',
  muscle_gain: 'Набор массы',
  detox: 'Детокс',
  keto: 'Кето',
  balanced: 'Сбалансированное питание',
}

function formatPrice(plan: MealPlan): { label: string; tone: 'success' | 'primary' | 'secondary' } {
  if (plan.is_free ?? plan.price_stars == null) {
    return { label: 'Бесплатно', tone: 'success' }
  }
  if (plan.price_stars != null) {
    return { label: `${plan.price_stars.toLocaleString('ru-RU')} Stars`, tone: 'primary' }
  }
  const amount = plan.price_amount ? Number.parseFloat(plan.price_amount) : null
  if (amount && Number.isFinite(amount)) {
    return {
      label: `${new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: plan.price_currency || 'RUB',
        maximumFractionDigits: 0,
      }).format(amount)}`,
      tone: 'primary',
    }
  }
  return { label: '—', tone: 'secondary' }
}

function formatCalories(value?: number | null): string {
  if (!value || !Number.isFinite(value)) {
    return '—'
  }
  return `${Math.max(0, Math.round(value))} ккал`
}

function formatDuration(days?: number | null): string {
  if (!days || !Number.isFinite(days)) {
    return 'Гибкий график'
  }
  if (days === 1) {
    return '1 день'
  }
  if (days < 7) {
    return `${days} дня`
  }
  if (days % 7 === 0) {
    const weeks = Math.round(days / 7)
    return `${weeks} нед${weeks === 1 ? 'еля' : 'ели'}`
  }
  return `${days} дней`
}

interface MealPlanCardProps {
  plan: MealPlan
  to: string
  className?: string
}

export function MealPlanCard({ plan, to, className }: MealPlanCardProps) {
  const price = formatPrice(plan)
  const goalLabel = plan.goal ? GOAL_LABELS[plan.goal] ?? plan.goal : null
  const tags = Array.isArray(plan.tags) ? plan.tags.slice(0, 3) : []
  const macros = plan.nutrition_totals

  return (
    <Card
      as={Link}
      to={to}
      className={clsx(
        'group flex h-full flex-col gap-4 rounded-3xl border border-border/70 bg-card/80 p-5 shadow-level-2 transition hover:border-primary/60 hover:shadow-level-3',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-foreground line-clamp-2">{plan.title}</h3>
            {goalLabel ? <Badge tone="primary" size="sm">{goalLabel}</Badge> : null}
          </div>
          {plan.description ? (
            <p className="text-sm text-muted-foreground line-clamp-2">{plan.description}</p>
          ) : null}
        </div>
        <Badge tone={price.tone} className="gap-1 whitespace-nowrap">
          {plan.price_stars != null ? <StarIcon className="h-4 w-4" aria-hidden="true" /> : null}
          {price.label}
        </Badge>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1 rounded-full bg-muted/20 px-2 py-1">
          <CalendarDaysIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {formatDuration(plan.duration_days)}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-muted/20 px-2 py-1">
          <FlameIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {formatCalories(plan.calories_per_day ?? plan.total_calories)}
        </span>
        {tags.length > 0 ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/20 px-2 py-1">
            <TagsIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {tags.map(tag => `#${tag}`).join(' ')}
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.3em] text-muted-foreground">Ккал</span>
          <span className="text-sm font-semibold text-foreground">{formatCalories(macros?.calories)}</span>
        </div>
        <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.3em] text-muted-foreground">Белки</span>
          <span className="text-sm font-semibold text-foreground">{Math.round(macros?.protein_g ?? 0)} г</span>
        </div>
        <div className="flex flex-col rounded-2xl bg-muted/15 px-3 py-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.3em] text-muted-foreground">Жиры</span>
          <span className="text-sm font-semibold text-foreground">{Math.round(macros?.fat_g ?? 0)} г</span>
        </div>
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <LayersIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {plan.items.length} позиций
        </span>
        <span className="inline-flex items-center gap-1">
          <CalendarDaysIcon className="h-3.5 w-3.5" aria-hidden="true" />
          Обновлено {new Date(plan.updated_at).toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' })}
        </span>
      </div>
    </Card>
  )
}

export default MealPlanCard
