import { useMemo } from 'react'
import { SparklesIcon, XIcon } from 'lucide-react'

import { Button, Card, Badge } from '../../../components/ui'
import type {
  MarketProduct,
  MarketRecipe,
  MarketResource,
  MarketStore,
} from '../../../types/market'
import { MARKET_RESOURCE_LABELS } from '../../market/constants'

export interface MarketUpdateEntry {
  id: string
  resource: MarketResource
  action?: string
  occurredAt?: string
  product?: MarketProduct
  recipe?: MarketRecipe
  store?: MarketStore
}

interface MarketUpdatesPanelProps {
  updates: MarketUpdateEntry[]
  onClear: () => void
  onDismiss: () => void
}

function formatTimestamp(value?: string): string | null {
  if (!value) return null
  try {
    const formatter = new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
    return formatter.format(new Date(value))
  } catch (_error) {
    return value
  }
}

function resolveHeadline(update: MarketUpdateEntry): string {
  const action = update.action ?? 'updated'
  switch (update.resource) {
    case 'products':
      if (action === 'created') return 'Новый товар в каталоге'
      if (action === 'published') return 'Товар опубликован'
      if (action === 'status_changed') return 'Статус товара обновлён'
      return 'Обновление товара'
    case 'recipes':
      if (action === 'created') return 'Новый рецепт добавлен'
      if (action === 'published') return 'Рецепт опубликован'
      return 'Обновление рецепта'
    case 'stores':
      if (action === 'created') return 'Новый магазин подключён'
      if (action === 'verified') return 'Магазин подтверждён'
      if (action === 'status_changed') {
        return update.store?.is_active ? 'Магазин снова открыт' : 'Магазин приостановлен'
      }
      return 'Обновление магазина'
    default:
      return 'Обновление маркетплейса'
  }
}

function resolveTitle(update: MarketUpdateEntry): string {
  if (update.resource === 'products') {
    return update.product?.title ?? 'Без названия'
  }
  if (update.resource === 'recipes') {
    return update.recipe?.title ?? 'Без названия'
  }
  return update.store?.name ?? 'Магазин'
}

function resolveSubtitle(update: MarketUpdateEntry): string | null {
  if (update.resource === 'products') {
    const storeName = update.product?.store_name
    const price = Number.isFinite(update.product?.price)
      ? `${Number(update.product?.price ?? 0).toLocaleString('ru-RU')} ${update.product?.currency ?? '₽'}`
      : null
    if (storeName && price) return `${storeName} · ${price}`
    if (storeName) return storeName
    if (price) return price
    return null
  }
  if (update.resource === 'recipes') {
    const store = update.recipe?.store_name
    const calories = Number.isFinite(update.recipe?.calories)
      ? `${Number(update.recipe?.calories ?? 0).toLocaleString('ru-RU')} ккал`
      : null
    if (store && calories) return `${store} · ${calories}`
    if (store) return store
    if (calories) return calories
    return null
  }
  const city = update.store?.city
  const verified = update.store?.is_verified
  if (city && verified) return `${city} · Проверен`
  if (city) return city
  if (verified) return 'Проверен маркетплейсом'
  return null
}

function resolveHref(resource: MarketResource): string {
  switch (resource) {
    case 'products':
      return '/market/products'
    case 'recipes':
      return '/market/recipes'
    case 'stores':
    default:
      return '/market/stores'
  }
}

export function MarketUpdatesPanel({ updates, onClear, onDismiss }: MarketUpdatesPanelProps) {
  const entries = useMemo(() => updates.slice(0, 4), [updates])

  if (entries.length === 0) return null

  return (
    <Card elevation={2} className="border-primary/40 bg-primary/5 px-5 py-4">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-primary">
            <SparklesIcon className="h-5 w-5 flex-none" aria-hidden="true" />
            <div className="flex flex-col">
              <span className="text-sm font-semibold uppercase tracking-wide text-primary/80">
                Маркетплейс обновился
              </span>
              <span className="text-sm text-primary/70">
                Новые предложения доступны прямо сейчас — успейте посмотреть.
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onDismiss} leadingIcon={<XIcon className="h-4 w-4" />}>
              Скрыть
            </Button>
            <Button variant="outline" size="sm" onClick={onClear}>
              Очистить
            </Button>
          </div>
        </div>
        <div className="grid gap-3">
          {entries.map(update => {
            const timestamp = formatTimestamp(update.occurredAt)
            const headline = resolveHeadline(update)
            const title = resolveTitle(update)
            const subtitle = resolveSubtitle(update)
            const href = resolveHref(update.resource)
            return (
              <div
                key={update.id}
                className="flex flex-col gap-2 rounded-2xl border border-primary/30 bg-background/95 px-4 py-3 shadow-sm shadow-black/5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-primary/80">
                    <Badge tone="primary" className="text-[11px] uppercase tracking-[0.25em]">
                      {MARKET_RESOURCE_LABELS[update.resource]}
                    </Badge>
                    <span className="font-semibold text-primary/80">{headline}</span>
                    {timestamp ? <time className="text-primary/60" dateTime={update.occurredAt}>{timestamp}</time> : null}
                  </div>
                  <span className="text-sm font-semibold text-foreground [overflow-wrap:anywhere]">{title}</span>
                  {subtitle ? (
                    <span className="text-xs text-muted-foreground [overflow-wrap:anywhere]">{subtitle}</span>
                  ) : null}
                </div>
                <div className="flex items-center gap-2 pt-1 sm:pt-0">
                  <Button variant="primary" size="sm" href={href}>
                    Открыть каталог
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

export default MarketUpdatesPanel
