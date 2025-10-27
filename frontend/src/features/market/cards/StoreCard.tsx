import { ExternalLinkIcon, MapPinIcon, TimerIcon } from 'lucide-react'

import type { MarketStore } from '../../../types/market'
import { Badge, Button, Card, Rating } from '../../../components/ui'

export interface StoreCardProps {
  item: MarketStore
}

function formatDeliveryEta(value?: number | null): string {
  if (!value || value <= 0) return 'от 30 мин'
  if (value < 60) return `${value} мин`
  const hours = Math.floor(value / 60)
  const minutes = value % 60
  if (minutes === 0) return `${hours} ч`
  return `${hours} ч ${minutes} мин`
}

function formatDeliveryPrice(value?: number | null, currency?: string | null): string | null {
  if (value == null) return null
  try {
    return value === 0
      ? 'бесплатно'
      : value.toLocaleString('ru-RU', {
          style: 'currency',
          currency: currency || 'RUB',
        })
  } catch (_error) {
    return `${value} ${currency ?? '₽'}`
  }
}

export function StoreCard({ item }: StoreCardProps) {
  const deliveryEta = formatDeliveryEta(item.delivery_eta_minutes ?? undefined)
  const deliveryPrice = formatDeliveryPrice(item.delivery_price ?? undefined, item.currency)

  return (
    <Card interactive elevation={2} className="flex flex-col gap-4 p-0 sm:flex-row">
      <div className="flex h-40 w-full flex-none overflow-hidden rounded-l-2xl bg-muted/30 sm:h-auto sm:w-48">
        {item.hero_image_url ? (
          <img src={item.hero_image_url} alt={item.name} className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <MapPinIcon className="h-5 w-5" aria-hidden="true" />
            <span>Партнёр NutriBot</span>
          </div>
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-4 px-5 py-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="text-title font-semibold text-foreground [overflow-wrap:anywhere]">{item.name}</h3>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <MapPinIcon className="h-4 w-4" aria-hidden="true" />
              <span className="font-medium text-foreground/80">{item.city}</span>
              {item.tags?.slice(0, 2).map(tag => (
                <Badge key={tag} tone="muted" className="!text-[10px] !tracking-[0.2em]">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
          {item.rating ? <Rating value={item.rating} count={item.rating_count ?? undefined} size="sm" /> : null}
        </div>
        {item.description ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.description}</p> : null}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-full bg-muted/25 px-2 py-1">
            <TimerIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {deliveryEta}
          </span>
          {deliveryPrice ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted/25 px-2 py-1">
              Доставка {deliveryPrice}
            </span>
          ) : null}
          {item.is_online ? <Badge tone="success">Онлайн</Badge> : null}
        </div>
        <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {item.rating_count ? <span>{item.rating_count} отзывов</span> : null}
            {item.delivery_price === 0 ? <span>Бесплатная доставка</span> : null}
          </div>
          {item.link_url ? (
            <Button
              variant="secondary"
              size="sm"
              className="gap-2"
              onClick={() => window.open(item.link_url ?? '#', '_blank', 'noopener')}
            >
              Перейти
              <ExternalLinkIcon className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  )
}

export default StoreCard