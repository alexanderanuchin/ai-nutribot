import { FlameIcon, HeartIcon, ShoppingCartIcon, StarIcon } from 'lucide-react'
import type { RecipeFeedItem } from '../../../types/feed'

export interface RecipeCardProps {
  item: RecipeFeedItem
  onOpenPremium?: (recipe: RecipeFeedItem) => void
}

export function RecipeCard({ item, onOpenPremium }: RecipeCardProps) {
  const macros = [
    { label: 'Б', value: item.protein },
    { label: 'Ж', value: item.fat },
    { label: 'У', value: item.carbs },
  ]
  const priceLabel = item.is_premium ? `${Number(item.price).toLocaleString('ru-RU')} ${item.currency}` : 'Бесплатно'

  return (
    <article className="flex flex-col gap-3 rounded-3xl border border-border/60 bg-background/90 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-xl">
      {item.hero_image ? (
        <div className="relative h-48 overflow-hidden rounded-3xl">
          <img src={item.hero_image} alt={item.title} className="h-full w-full object-cover" loading="lazy" />
          {item.is_premium ? (
            <span className="absolute left-3 top-3 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
              Премиум
            </span>
          ) : null}
        </div>
      ) : null}
      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-semibold text-foreground">{item.title}</h3>
        <p className="text-sm text-muted-foreground">{item.short_description}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div className="flex items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <FlameIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div>
            <div className="text-xs text-muted-foreground">Калории</div>
            <div className="font-semibold">{item.calories} ккал</div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <ShoppingCartIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div>
            <div className="text-xs text-muted-foreground">Покупки</div>
            <div className="font-semibold">{item.purchases_count}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <StarIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <div>
            <div className="text-xs text-muted-foreground">Рейтинг</div>
            <div className="font-semibold">{Number(item.rating).toFixed(1)} / 5</div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-muted/40 px-3 py-2">
          <span className="text-lg font-semibold text-primary">{priceLabel}</span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-full bg-muted/30 px-2 py-1">{item.cook_time_minutes} мин</span>
        <span className="rounded-full bg-muted/30 px-2 py-1">Сложность: {item.difficulty}</span>
        {macros.map(macro => (
          <span key={macro.label} className="rounded-full bg-primary/10 px-2 py-1 font-semibold text-primary">
            {macro.label}: {macro.value} г
          </span>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border/60 text-primary transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-label="Поставить лайк"
          >
            <HeartIcon className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        {item.is_premium ? (
          <button
            type="button"
            onClick={() => onOpenPremium?.(item)}
            className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
          >
            Открыть премиум
          </button>
        ) : null}
      </div>
    </article>
  )
}

export default RecipeCard