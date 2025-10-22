import { useMemo, useState } from 'react'

import { ImageOff, MapPinIcon, ShoppingBagIcon } from 'lucide-react'

import type { DealFeedItem } from '../../../types/feed'

export interface DealCardProps {
  item: DealFeedItem
}

function formatPrice(price: string): string {
  return `${Number(price).toLocaleString('ru-RU')} ₽`
}

function formatValidUntil(value: string): string {
  try {
    return new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short' }).format(new Date(value))
  } catch (_error) {
    return value
  }
}

export function DealCard({ item }: DealCardProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const shouldShowImage = Boolean(item.image_url) && !imageFailed

  const mediaNode = useMemo(() => {
    if (shouldShowImage) {
      return (
        <img
          src={item.image_url}
          alt={item.product_name}
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
  }, [item.image_url, item.product_name, shouldShowImage])

  return (
    <article className="flex flex-col gap-4 overflow-hidden rounded-3xl border border-border/60 bg-background/95 p-4 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg sm:flex-row">
      <div className="overflow-hidden rounded-2xl bg-muted/60 sm:w-32 sm:flex-shrink-0">
        <div className="aspect-[4/3] w-full">{mediaNode}</div>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <ShoppingBagIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="font-semibold text-foreground [overflow-wrap:anywhere]">{item.network}</span>
          <span className="hidden h-1 w-1 rounded-full bg-border/80 sm:inline-flex" aria-hidden="true" />
          <span className="truncate">до {formatValidUntil(item.valid_until)}</span>
          {item.is_online ? (
            <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
              Онлайн
            </span>
          ) : null}
        </div>
        <h3 className="line-clamp-2 text-base font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="rounded-full bg-muted/40 px-2 py-1 font-semibold text-primary">
            -{Number(item.discount_percent).toFixed(0)}%
          </span>
          <div className="flex min-w-0 flex-wrap items-baseline gap-2 [overflow-wrap:anywhere]">
            <span className="text-lg font-semibold text-foreground">{formatPrice(item.price_after)}</span>
            <span className="text-xs text-muted-foreground line-through">{formatPrice(item.price_before)}</span>
          </div>
        </div>
        <div className="mt-auto flex flex-wrap items-center gap-2 text-xs text-muted-foreground [overflow-wrap:anywhere]">
          <MapPinIcon className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="font-medium text-foreground/80">{item.city}</span>
          {item.address ? <span className="text-muted-foreground">· {item.address}</span> : null}
        </div>
      </div>
    </article>
  )
}

export default DealCard