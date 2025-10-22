import { useMemo, useState } from 'react'

import { FlameIcon, HeartIcon, ImageOff, ShoppingCartIcon, StarIcon } from 'lucide-react'

import type { RecipeFeedItem } from '../../../types/feed'

export interface RecipeCardProps {
  item: RecipeFeedItem
  onOpenPremium?: (recipe: RecipeFeedItem) => void
}

export function RecipeCard({ item, onOpenPremium }: RecipeCardProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const macros = [
    { label: 'Б', value: item.protein },
    { label: 'Ж', value: item.fat },
    { label: 'У', value: item.carbs },
  ]
  const priceLabel = item.is_premium ? `${Number(item.price).toLocaleString('ru-RU')} ${item.currency}` : 'Бесплатно'
  const shouldShowImage = Boolean(item.hero_image) && !imageFailed

  const mediaNode = useMemo(() => {
    if (shouldShowImage) {
      return (
        <img
          src={item.hero_image}
          alt={item.title}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => setImageFailed(true)}
        />
      )
    }
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-xs font-medium text-muted-foreground">
        <ImageOff className="h-6 w-6" aria-hidden="true" />
        <span className="truncate">Нет изображения</span>
      </div>
    )
  }, [item.hero_image, item.title, shouldShowImage])

  return (
    <article className="flex flex-col gap-4 overflow-hidden rounded-3xl border border-border/60 bg-background/90 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-xl">
      <div className="relative overflow-hidden rounded-3xl bg-muted/60">
        <div className="aspect-[4/3] w-full">{mediaNode}</div>
        {item.is_premium ? (
          <span className="absolute left-3 top-3 inline-flex min-h-[2rem] items-center rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground shadow-soft">
            Премиум
          </span>
        ) : null}
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="line-clamp-2 text-lg font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
        <p className="line-clamp-3 text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.short_description}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div className="flex min-w-0 items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <FlameIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground">Калории</div>
            <div className="text-sm font-semibold text-foreground [overflow-wrap:anywhere]">{item.calories} ккал</div>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <ShoppingCartIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground">Покупки</div>
            <div className="text-sm font-semibold text-foreground [overflow-wrap:anywhere]">{item.purchases_count}</div>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <StarIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground">Рейтинг</div>
            <div className="text-sm font-semibold text-foreground [overflow-wrap:anywhere]">{Number(item.rating).toFixed(1)} / 5</div>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <span className="text-sm font-semibold text-primary [overflow-wrap:anywhere]">{priceLabel}</span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-full bg-muted/30 px-2 py-1">{item.cook_time_minutes} мин</span>
        <span className="rounded-full bg-muted/30 px-2 py-1 [overflow-wrap:anywhere]">Сложность: {item.difficulty}</span>
        {macros.map(macro => (
          <span key={macro.label} className="rounded-full bg-primary/10 px-2 py-1 font-semibold text-primary">
            {macro.label}: {macro.value} г
          </span>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="flex h-11 w-11 items-center justify-center rounded-full border border-border/60 text-primary transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Поставить лайк"
        >
          <HeartIcon className="h-5 w-5" aria-hidden="true" />
        </button>
        {item.is_premium ? (
          <button
            type="button"
            onClick={() => onOpenPremium?.(item)}
            className="inline-flex min-h-[2.75rem] flex-1 items-center justify-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 sm:flex-none sm:px-6"
          >
            Открыть премиум
          </button>
        ) : null}
      </div>
    </article>
  )
}

export default RecipeCard