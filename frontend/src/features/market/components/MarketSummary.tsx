import { useMemo } from 'react'
import clsx from 'clsx'

import { useSafeArea } from '../../../hooks/useSafeArea'
import { Button, Card } from '../../../components/ui'
import { ShoppingCartIcon, UtensilsCrossedIcon } from 'lucide-react'
import type { selectCartTotals } from '../stores/cartStore'
import type { selectPlanTotals } from '../stores/planStore'
import type { MarketCheckoutInsights } from '../hooks/useMarketCheckout'

interface MarketSummarySidebarProps {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
  insights: MarketCheckoutInsights
  onCheckoutRub: () => void
  onCheckoutCalo: () => void
  checkoutMode: 'rub' | 'calo' | null
}

export function MarketSummarySidebar({
  cart,
  plan,
  insights,
  onCheckoutRub,
  onCheckoutCalo,
  checkoutMode,
}: MarketSummarySidebarProps) {
  const priceFormatter = useMemo(
    () =>
      cart.currency
        ? new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: cart.currency,
            maximumFractionDigits: 0,
          })
        : null,
    [cart.currency],
  )
  const caloFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  )
  const rubSummary = cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : 'Добавьте продукты из каталога'
  const caloSummary =
    insights.caloEquivalent && insights.caloRate
      ? `≈ ${caloFormatter.format(insights.caloEquivalent)} CALO · ${caloFormatter.format(insights.caloRate)} ₽/CALO`
      : 'Настройте курс CaloCoin, чтобы видеть эквивалент'
  const caloBalanceHint =
    insights.caloBalance !== null
      ? `Баланс: ${caloFormatter.format(Math.max(0, insights.caloBalance))} CALO`
      : null
  const rubButtonLabel =
    cart.amount > 0 && priceFormatter ? `Оплатить ${priceFormatter.format(cart.amount)}` : 'Оформить заказ'
  const caloButtonLabel =
    insights.caloEquivalent && insights.caloEquivalent > 0
      ? `Оплатить ${caloFormatter.format(insights.caloEquivalent)} CALO`
      : 'Оплатить CaloCoin'

  return (
    <div className="hidden xl:block xl:sticky xl:top-28">
      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-4" elevation={2}>
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">Корзина</span>
              <span className="text-title font-semibold text-foreground">{cart.quantity} позиций</span>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <ShoppingCartIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{rubSummary}</p>
          <p className="text-xs text-muted-foreground">{caloSummary}</p>
          {caloBalanceHint ? <p className="text-xs text-muted-foreground">{caloBalanceHint}</p> : null}
          <div className="flex flex-col gap-2 pt-1">
            <Button
              type="button"
              variant="primary"
              size="md"
              onClick={onCheckoutRub}
              disabled={!insights.canCheckout || checkoutMode === 'calo'}
              loading={checkoutMode === 'rub'}
              title={!insights.canCheckout ? 'Добавьте товары в корзину, чтобы оформить заказ' : undefined}
            >
              {rubButtonLabel}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={onCheckoutCalo}
              disabled={!insights.canPayWithCalo || checkoutMode === 'rub'}
              loading={checkoutMode === 'calo'}
              title={!insights.canPayWithCalo ? 'Недостаточно CaloCoin на счёте или не задан курс' : undefined}
            >
              {caloButtonLabel}
            </Button>
          </div>
        </Card>
        <Card className="flex flex-col gap-4" elevation={2}>
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-muted-foreground">План питания</span>
              <span className="text-title font-semibold text-foreground">{plan.count} рецептов</span>
            </div>
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <UtensilsCrossedIcon className="h-6 w-6" aria-hidden="true" />
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {plan.servings > 0
              ? `${plan.servings} порций · ${plan.calories.toLocaleString('ru-RU')} ккал`
              : 'Добавьте блюда в индивидуальный план'}
          </p>
          <Button variant="secondary" size="md" href="/market/recipes">
            Собрать меню
          </Button>
        </Card>
      </div>
    </div>
  )
}

interface MarketSummaryMobileBarProps {
  cart: ReturnType<typeof selectCartTotals>
  plan: ReturnType<typeof selectPlanTotals>
  insights: MarketCheckoutInsights
  onFilters: () => void
  onSearch: () => void
  onCheckoutRub: () => void
  onCheckoutCalo: () => void
  checkoutMode: 'rub' | 'calo' | null
}

export function MarketSummaryMobileBar({
  cart,
  plan,
  insights,
  onFilters,
  onSearch,
  onCheckoutRub,
  onCheckoutCalo,
  checkoutMode,
}: MarketSummaryMobileBarProps) {
  const safeArea = useSafeArea({ inset: 12, edges: ['left', 'right'] })
  const priceFormatter = cart.currency
    ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: cart.currency, maximumFractionDigits: 0 })
    : null
  const caloFormatter = useMemo(
    () =>
      new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  )
  const rubAmount = cart.amount > 0 && priceFormatter ? priceFormatter.format(cart.amount) : '0 ₽'
  const caloAmount =
    insights.caloEquivalent && insights.caloEquivalent > 0
      ? `${caloFormatter.format(insights.caloEquivalent)} CALO`
      : 'CaloCoin'
  const caloSummary =
    insights.caloRate && insights.caloEquivalent
      ? `≈ ${caloFormatter.format(insights.caloEquivalent)} CALO · ${caloFormatter.format(insights.caloRate)} ₽/CALO`
      : 'Курс CaloCoin пока не задан'

  return (
    <div
      className={clsx(
        'fixed inset-x-0 z-50 flex items-start justify-between gap-3 rounded-t-2xl border border-border/70 bg-card/95 px-4 py-3 shadow-level-3 backdrop-blur lg:hidden box-border max-w-[100vw] [overflow-x:clip]'
      )}
      style={{
        ...safeArea,
        paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 0.75rem)',
        bottom: 'calc(var(--mobile-tab-bar-height, 72px) + 0.75rem)',
      }}
    >
      <div className="flex flex-col gap-1">
        <Button variant="ghost" size="sm" className="min-w-[92px]" onClick={onFilters}>
          Фильтры
        </Button>
        <Button variant="ghost" size="sm" className="min-w-[92px]" onClick={onSearch}>
          Поиск
        </Button>
      </div>
      <div className="flex flex-1 flex-col gap-1 text-xs text-muted-foreground">
        <div className="flex items-center justify-between text-sm text-foreground">
          <span>Корзина · {cart.quantity}</span>
          <span>{rubAmount}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>План · {plan.count}</span>
          <span>{plan.servings > 0 ? `${plan.servings} порций` : 'Пусто'}</span>
        </div>
        <div className="text-[11px] text-muted-foreground">{caloSummary}</div>
      </div>
      <div className="flex flex-col gap-1">
        <Button
          type="button"
          variant="primary"
          size="sm"
          className="min-w-[120px] whitespace-nowrap"
          onClick={onCheckoutRub}
          disabled={!insights.canCheckout || checkoutMode === 'calo'}
          loading={checkoutMode === 'rub'}
        >
          Оплатить {rubAmount}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-w-[120px] whitespace-nowrap"
          onClick={onCheckoutCalo}
          disabled={!insights.canPayWithCalo || checkoutMode === 'rub'}
          loading={checkoutMode === 'calo'}
        >
          Оплатить {caloAmount}
        </Button>
      </div>
    </div>
  )
}
