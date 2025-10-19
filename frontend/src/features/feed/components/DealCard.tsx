import { MapPinIcon, ShoppingBagIcon } from 'lucide-react'
import type { DealFeedItem } from '../../../types/feed'

export interface DealCardProps {
  item: DealFeedItem
}

function formatPrice(price: string): string {
  return `${Number(price).toLocaleString('ru-RU')} ₽`
}

export function DealCard({ item }: DealCardProps) {
  return (
    <article className="flex gap-4 rounded-3xl border border-border/60 bg-background/95 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg">
      {item.image_url ? (
        <div className="hidden h-24 w-24 shrink-0 overflow-hidden rounded-2xl sm:block">
          <img src={item.image_url} alt={item.product_name} className="h-full w-full object-cover" loading="lazy" />
        </div>
      ) : null}
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShoppingBagIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="font-semibold text-foreground">{item.network}</span>
          <span>до {new Date(item.valid_until).toLocaleDateString('ru-RU')}</span>
          {item.is_online ? <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">Онлайн</span> : null}
        </div>
        <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
        <div className="flex items-center gap-3 text-sm">
          <span className="rounded-full bg-muted/40 px-2 py-1 font-semibold text-primary">
            -{Number(item.discount_percent).toFixed(0)}%
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-semibold text-foreground">{formatPrice(item.price_after)}</span>
            <span className="text-xs text-muted-foreground line-through">{formatPrice(item.price_before)}</span>
          </div>
        </div>
        <div className="mt-auto flex items-center gap-2 text-xs text-muted-foreground">
          <MapPinIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <span>{item.city}</span>
          {item.address ? <span>· {item.address}</span> : null}
        </div>
      </div>
    </article>
  )
}

export default DealCard