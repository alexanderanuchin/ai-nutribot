import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRightIcon, ShoppingCartIcon, UtensilsCrossedIcon } from 'lucide-react'

import { fetchMarketCollection } from '../../api/market'
import MarketPageHeader from '../../features/market/components/MarketPageHeader'
import MarketListSkeleton from '../../features/market/components/MarketListSkeleton'
import RecipeCard from '../../features/market/cards/RecipeCard'
import ProductCard from '../../features/market/cards/ProductCard'
import StoreCard from '../../features/market/cards/StoreCard'
import { MARKET_RESOURCE_DESCRIPTION, MARKET_RESOURCE_TITLE } from '../../features/market/constants'
import { useMarketCartStore, selectCartTotals } from '../../features/market/stores/cartStore'
import { useMarketPlanStore, selectPlanTotals } from '../../features/market/stores/planStore'
import { Card } from '../../components/ui'

export function MarketHubPage() {
  const cartTotals = useMarketCartStore(
    selectCartTotals,
    (a, b) =>
      a.count === b.count &&
      a.quantity === b.quantity &&
      a.amount === b.amount &&
      a.currency === b.currency,
  )
  const planTotals = useMarketPlanStore(
    selectPlanTotals,
    (a, b) => a.count === b.count && a.servings === b.servings && a.calories === b.calories,
  )

  const recipesQuery = useQuery({
    queryKey: ['market', 'hub', 'recipes'],
    queryFn: () => fetchMarketCollection({ resource: 'recipes', pageSize: 3 }),
  })
  const productsQuery = useQuery({
    queryKey: ['market', 'hub', 'products'],
    queryFn: () => fetchMarketCollection({ resource: 'products', pageSize: 3 }),
  })
  const storesQuery = useQuery({
    queryKey: ['market', 'hub', 'stores'],
    queryFn: () => fetchMarketCollection({ resource: 'stores', pageSize: 3 }),
  })

  const cartCurrency = cartTotals.currency ?? 'RUB'
  const priceFormatter = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: cartCurrency, maximumFractionDigits: 0 })

  const primaryLinkClass =
    'inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-level-2 transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
  const ghostLinkClass =
    'inline-flex items-center gap-2 rounded-full border border-border/60 px-3 py-2 text-sm font-semibold text-foreground transition hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

  return (
    <div className="flex flex-col gap-8 pb-8">
      <MarketPageHeader
        title="Маркет NutriBot"
        description="Соберите корзину, дополняйте план питания и открывайте партнёров доставки в один тап."
        action={
          <Link to="/market/recipes" className={primaryLinkClass}>
            Подобрать рацион
            <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
          </Link>
        }
      >
        <div className="grid gap-3 md:grid-cols-2">
          <Card elevation={2} className="flex items-center justify-between gap-4 p-5">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">В корзине</span>
              <span className="text-headline font-semibold text-foreground">{cartTotals.quantity} товаров</span>
              <span className="text-sm text-muted-foreground">
                {cartTotals.amount > 0 ? priceFormatter.format(cartTotals.amount) : 'Добавьте продукты из каталога'}
              </span>
            </div>
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <ShoppingCartIcon className="h-7 w-7" aria-hidden="true" />
            </span>
          </Card>
          <Card elevation={2} className="flex items-center justify-between gap-4 p-5">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">В плане</span>
              <span className="text-headline font-semibold text-foreground">{planTotals.count} рецептов</span>
              <span className="text-sm text-muted-foreground">
                {planTotals.servings > 0
                  ? `${planTotals.servings} порций · ${planTotals.calories.toLocaleString('ru-RU')} ккал`
                  : 'Добавьте блюда в индивидуальный план'}
              </span>
            </div>
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <UtensilsCrossedIcon className="h-7 w-7" aria-hidden="true" />
            </span>
          </Card>
        </div>
      </MarketPageHeader>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-headline font-semibold text-foreground">{MARKET_RESOURCE_TITLE.recipes}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.recipes}</p>
          </div>
          <Link to="/market/recipes" className={ghostLinkClass}>
            Все рецепты
            <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
        {recipesQuery.isLoading ? (
          <MarketListSkeleton variant="recipes" count={3} />
        ) : recipesQuery.data?.items?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {recipesQuery.data.items.map(item => (
              <RecipeCard key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <Card elevation={1} className="text-sm text-muted-foreground">
            Пока нет рекомендаций — настройте фильтры внутри раздела.
          </Card>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-headline font-semibold text-foreground">{MARKET_RESOURCE_TITLE.products}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.products}</p>
          </div>
          <Link to="/market/products" className={ghostLinkClass}>
            Все товары
            <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
        {productsQuery.isLoading ? (
          <MarketListSkeleton variant="products" count={3} />
        ) : productsQuery.data?.items?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {productsQuery.data.items.map(item => (
              <ProductCard key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <Card elevation={1} className="text-sm text-muted-foreground">
            Ассортимент обновляется — загляните позже.
          </Card>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-headline font-semibold text-foreground">{MARKET_RESOURCE_TITLE.stores}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.stores}</p>
          </div>
          <Link to="/market/stores" className={ghostLinkClass}>
            Все магазины
            <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
        {storesQuery.isLoading ? (
          <MarketListSkeleton variant="stores" count={3} />
        ) : storesQuery.data?.items?.length ? (
          <div className="flex flex-col gap-4">
            {storesQuery.data.items.map(item => (
              <StoreCard key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <Card elevation={1} className="text-sm text-muted-foreground">
            Партнёры ещё подключаются — мы уведомим о запуске.
          </Card>
        )}
      </section>
    </div>
  )
}

export default MarketHubPage