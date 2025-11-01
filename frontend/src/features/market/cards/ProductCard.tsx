import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckIcon, ShoppingBagIcon } from 'lucide-react'

import type { MarketProduct } from '../../../types/market'
import { submitCartItem } from '../cart/api'
import { createCartSubmissionPayload } from '../cart/form'
import {
  selectCartQuantity,
  useMarketCartStore,
} from '../stores/cartStore'
import { Badge, Button, Card, Price, QuantityStepper, Rating, useToast } from '../../../components/ui'

export interface ProductCardProps {
  item: MarketProduct
}

export function ProductCard({ item }: ProductCardProps) {
  const hydrated = useMarketCartStore(state => state.hydrated)
  const addItem = useMarketCartStore(state => state.addItem)
  const removeItem = useMarketCartStore(state => state.removeItem)
  const setQuantity = useMarketCartStore(state => state.setQuantity)
  const quantity = useMarketCartStore(selectCartQuantity('product', item.id))
  const [imageFailed, setImageFailed] = useState(false)
  const { notify } = useToast()

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
    [item.currency, item.id, item.image_url, item.price, item.title, item.unit],
  )

  const mutation = useMutation({
    mutationFn: async (nextQuantity: number) => {
      const submission = createCartSubmissionPayload({
        product_id: item.id,
        quantity: Math.max(nextQuantity, 0),
      })
      return submitCartItem(submission)
    },
    onSuccess: response => {
      const updatedQuantity = response.item?.quantity ?? 0
      if (response.status === 'removed' || updatedQuantity <= 0) {
        removeItem('product', item.id)
        return
      }
      if (!hydrated) return
      if (quantity <= 0) {
        addItem({ ...base, quantity: updatedQuantity })
        notify({
          title: 'Добавлено в корзину',
          description: `${item.title} × ${updatedQuantity}`,
          tone: 'success',
        })
        return
      }
      setQuantity(base, updatedQuantity)
    },
  })

  const handleSetQuantity = (nextQuantity: number) => {
    mutation.mutate(nextQuantity)
  }

  const displayImage = !imageFailed && item.image_url ? item.image_url : null

  return (
    <Card interactive elevation={2} className="flex h-full flex-col gap-4 p-0">
      <div className="relative overflow-hidden rounded-t-2xl">
        <div className="relative aspect-square w-full overflow-hidden bg-muted/15">
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
        </div>
        <div className="absolute inset-x-0 top-3 flex items-center justify-between px-3">
          {item.discount_percent ? (
            <Badge tone="primary">-{Number(item.discount_percent).toFixed(0)}%</Badge>
          ) : null}
          {!item.available ? <Badge tone="warning">Нет в наличии</Badge> : null}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-4 px-5 pb-5">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="text-title font-semibold text-foreground [overflow-wrap:anywhere]">{item.title}</h3>
          {item.subtitle ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{item.subtitle}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Price value={item.price} currency={item.currency} originalValue={item.price_original ?? null} />
          {item.unit ? <span className="text-xs text-muted-foreground">/ {item.unit}</span> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {item.brand ? <span className="rounded-full bg-muted/20 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.2em]">{item.brand}</span> : null}
          {item.badges?.map(badge => (
            <span key={badge} className="rounded-full bg-muted/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em]">
              {badge}
            </span>
          ))}
        </div>
        <div className="flex items-center justify-between gap-3">
          {item.rating ? <Rating value={item.rating} count={item.rating_count ?? undefined} size="sm" /> : <span className="text-xs text-muted-foreground">Рейтинг появится после продаж</span>}
          {quantity > 0 ? (
            <QuantityStepper
              value={quantity}
              min={0}
              onChange={value => handleSetQuantity(value)}
              disabled={mutation.isPending}
            />
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleSetQuantity(1)}
              disabled={!hydrated || mutation.isPending || !item.available}
              leadingIcon={<CheckIcon className="h-4 w-4" aria-hidden="true" />}
            >
              В корзину
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

export default ProductCard