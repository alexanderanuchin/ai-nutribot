import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckIcon, Loader2Icon, MinusIcon, PlusIcon, ShoppingBagIcon } from 'lucide-react'
import clsx from 'clsx'

import type { MarketProduct } from '../../../types/market'
import { addProductToCart } from '../../../api/market'
import {
  selectCartQuantity,
  useMarketCartStore,
} from '../stores/cartStore'

export interface ProductCardProps {
  item: MarketProduct
}

function formatCurrency(amount: number, currency: string): string {
  try {
    return amount.toLocaleString('ru-RU', { style: 'currency', currency })
  } catch (_error) {
    return `${amount.toFixed(0)} ${currency}`
  }
}

export function ProductCard({ item }: ProductCardProps) {
  const hydrated = useMarketCartStore(state => state.hydrated)
  const addItem = useMarketCartStore(state => state.addItem)
  const removeItem = useMarketCartStore(state => state.removeItem)
  const setQuantity = useMarketCartStore(state => state.setQuantity)
  const quantity = useMarketCartStore(selectCartQuantity('product', item.id))
  const [imageFailed, setImageFailed] = useState(false)

  const base = useMemo(
    () => ({
      kind: 'product' as const,
      id: item.id,
      title: item.title,
      price: item.price,
      currency: item.currency,
      imageUrl: item.image_url ?? null,
      unit: item.unit ?? null,
    }),
    [item.currency, item.id, item.image_url, item.price, item.title, item.unit]
  )

  const mutation = useMutation({
    mutationFn: async (nextQuantity: number) => {
      await addProductToCart({ product_id: item.id, quantity: Math.max(nextQuantity, 0) })
      return Math.max(nextQuantity, 0)
    },
    onSuccess: nextQuantity => {
      if (nextQuantity <= 0) {
        removeItem('product', item.id)
        return
      }
      if (!hydrated) return
      if (quantity <= 0) {
        addItem({ ...base, quantity: nextQuantity })
        return
      }
      setQuantity(base, nextQuantity)
    },
  })

  const handleAdd = () => {
    if (!hydrated || !item.available) return
    const nextQuantity = quantity > 0 ? quantity + 1 : 1
    mutation.mutate(nextQuantity)
  }

  const handleDecrease = () => {
    if (!hydrated) return
    if (quantity <= 0) return
    const nextQuantity = quantity - 1
    mutation.mutate(nextQuantity)
  }

  const handleIncrease = () => {
    if (!hydrated || !item.available) return
    const nextQuantity = quantity + 1
    mutation.mutate(nextQuantity)
  }

  const displayImage = !imageFailed && item.image_url ? item.image_url : null
  const priceDisplay = formatCurrency(item.price, item.currency)
  const originalPriceDisplay = item.price_original
    ? formatCurrency(item.price_original, item.currency)
    : null

  return (
    <article className="flex flex-col overflow-hidden rounded-3xl border border-border/60 bg-background/95 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="relative aspect-square w-full overflow-hidden bg-muted/20">
        {displayImage ? (
          <img
            src={displayImage}
            alt={item.title}
            loading="lazy"
            className="h-full w-full object-cover"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <ShoppingBagIcon className="h-6 w-6" aria-hidden="true" />
            <span>Без фото</span>
          </div>
        )}
        {item.discount_percent ? (
          <span className="absolute left-3 top-3 inline-flex items-center rounded-full bg-rose-500/90 px-2 py-1 text-[11px] font-semibold text-white">
            -{Number(item.discount_percent).toFixed(0)}%
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="text-base font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
          {item.subtitle ? (
            <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.subtitle}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-baseline gap-2 text-sm">
          <span className="text-lg font-semibold text-primary">{priceDisplay}</span>
          {originalPriceDisplay ? (
            <span className="text-xs text-muted-foreground line-through">{originalPriceDisplay}</span>
          ) : null}
          {item.unit ? <span className="text-xs text-muted-foreground">/ {item.unit}</span> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {item.brand ? (
            <span className="rounded-full bg-muted/40 px-2 py-1 text-[11px] font-medium uppercase tracking-wide">{item.brand}</span>
          ) : null}
          {item.badges?.map(badge => (
            <span key={badge} className="rounded-full bg-muted/30 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
              {badge}
            </span>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-3">
          {quantity > 0 ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDecrease}
                disabled={mutation.isPending}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-muted/60 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                {mutation.isPending ? (
                  <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <MinusIcon className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
              <span className="min-w-[2rem] text-center text-sm font-semibold text-foreground">{quantity}</span>
              <button
                type="button"
                onClick={handleIncrease}
                disabled={mutation.isPending || !item.available}
                className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                {mutation.isPending ? (
                  <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <PlusIcon className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleAdd}
              disabled={!hydrated || mutation.isPending || !item.available}
              className={clsx(
                'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                item.available ? 'bg-primary text-primary-foreground shadow-soft hover:bg-primary/90' : 'bg-muted text-muted-foreground'
              )}
            >
              {mutation.isPending ? (
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <CheckIcon className="h-4 w-4" aria-hidden="true" />
              )}
              {item.available ? 'В корзину' : 'Недоступно'}
            </button>
          )}
        </div>
      </div>
    </article>
  )
}

export default ProductCard