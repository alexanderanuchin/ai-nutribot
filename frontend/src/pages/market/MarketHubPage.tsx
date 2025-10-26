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

export function MarketHubPage() {
  const cartTotals = useMarketCartStore(selectCartTotals)
  const planTotals = useMarketPlanStore(selectPlanTotals)

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

  return (
    <div className="flex flex-col gap-8 pb-8">
      <MarketPageHeader
        title="Маркет NutriBot"
        description="Соберите корзину, дополняйте план питания и открывайте партнёров доставки в один тап."
        action={
          <Link
            to="/market/recipes"
            className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Подобрать рацион
            <ArrowRightIcon className="h-4 w-4" aria-hidden="true" />
          </Link>
        }
      >
        <div className="grid gap-3 md:grid-cols-2">
          <div className="flex items-center justify-between rounded-3xl border border-border/60 bg-background/90 px-4 py-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">В корзине</div>
              <div className="text-lg font-bold text-foreground">
                {cartTotals.quantity} товаров
              </div>
              <div className="text-xs text-muted-foreground">
                {cartTotals.amount > 0
                  ? cartTotals.amount.toLocaleString('ru-RU', {
                      style: 'currency',
                      currency: cartTotals.currency ?? 'RUB',
                    })
                  : 'Добавьте продукты из каталога'}
              </div>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <ShoppingCartIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
          <div className="flex items-center justify-between rounded-3xl border border-border/60 bg-background/90 px-4 py-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">В плане</div>
              <div className="text-lg font-bold text-foreground">
                {planTotals.count} рецептов
              </div>
              <div className="text-xs text-muted-foreground">
                {planTotals.servings > 0
                  ? `${planTotals.servings} порций · ${planTotals.calories} ккал`
                  : 'Добавьте блюда в индивидуальный план'}
              </div>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <UtensilsCrossedIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
        </div>
      </MarketPageHeader>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{MARKET_RESOURCE_TITLE.recipes}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.recipes}</p>
          </div>
          <Link
            to="/market/recipes"
            className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition hover:text-primary/80"
          >
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
          <div className="rounded-3xl border border-border/60 bg-muted/30 px-6 py-8 text-sm text-muted-foreground">
            Пока нет рекомендаций — настройте фильтры внутри раздела.
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{MARKET_RESOURCE_TITLE.products}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.products}</p>
          </div>
          <Link
            to="/market/products"
            className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition hover:text-primary/80"
          >
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
          <div className="rounded-3xl border border-border/60 bg-muted/30 px-6 py-8 text-sm text-muted-foreground">
            Ассортимент обновляется — загляните позже.
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{MARKET_RESOURCE_TITLE.stores}</h2>
            <p className="text-sm text-muted-foreground">{MARKET_RESOURCE_DESCRIPTION.stores}</p>
          </div>
          <Link
            to="/market/stores"
            className="inline-flex items-center gap-2 text-sm font-semibold text-primary transition hover:text-primary/80"
          >
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
          <div className="rounded-3xl border border-border/60 bg-muted/30 px-6 py-8 text-sm text-muted-foreground">
            Партнёры ещё подключаются — мы уведомим о запуске.
          </div>
        )}
      </section>
    </div>
  )
}

export default MarketHubPage