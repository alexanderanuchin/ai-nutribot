import { useCallback, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { isAxiosError } from 'axios'

import { checkoutCart } from '../cart/api'
import { useMarketCartStore, selectCartTotals } from '../stores/cartStore'
import { useMarketPlanStore, selectPlanTotals } from '../stores/planStore'
import { useAuth } from '../../../hooks/useAuth'
import { useToast } from '../../../components/ui'
import type { MarketCartCheckoutResponse } from '../../../types/market'

const parseNumeric = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseFloat(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export interface MarketCheckoutInsights {
  caloEquivalent: number | null
  caloRate: number | null
  caloBalance: number | null
  canPayWithCalo: boolean
  canCheckout: boolean
}

export function useMarketCheckout() {
  const cartTotals = useMarketCartStore(
    selectCartTotals,
    (a, b) =>
      a.count === b.count &&
      a.quantity === b.quantity &&
      a.amount === b.amount &&
      a.currency === b.currency,
  )
  const serverCart = useMarketCartStore(state => state.serverCart)
  const clearCart = useMarketCartStore(state => state.clear)

  const planTotals = useMarketPlanStore(
    selectPlanTotals,
    (a, b) => a.count === b.count && a.servings === b.servings && a.calories === b.calories,
  )

  const { profile } = useAuth()
  const { notify } = useToast()

  const caloRate = parseNumeric(profile?.calocoin_rate_rub)
  const caloBalance = parseNumeric(profile?.calocoin_balance)
  const caloEquivalent =
    caloRate && caloRate > 0 && cartTotals.amount > 0 ? cartTotals.amount / caloRate : null
  const canCheckoutRub = cartTotals.amount > 0 && Boolean(serverCart)
  const canPayWithCalo = Boolean(
    serverCart &&
      caloRate &&
      caloRate > 0 &&
      caloBalance !== null &&
      caloBalance > 0 &&
      caloEquivalent &&
      caloEquivalent > 0 &&
      caloBalance >= caloEquivalent,
  )

  const insights = useMemo<MarketCheckoutInsights>(
    () => ({
      caloEquivalent,
      caloRate,
      caloBalance,
      canPayWithCalo,
      canCheckout: canCheckoutRub,
    }),
    [caloBalance, caloEquivalent, caloRate, canCheckoutRub, canPayWithCalo],
  )

  const checkoutMutation = useMutation<
    MarketCartCheckoutResponse,
    unknown,
    { cartId: number; mode: 'rub' | 'calo' }
  >({
    mutationFn: async ({ cartId, mode }) => {
      const metadata = { source: 'market' }
      const payload =
        mode === 'calo'
          ? { pay_with_wallet: true, wallet_currency: 'CALO' as const, metadata }
          : { metadata }
      return checkoutCart(cartId, payload)
    },
    onSuccess: (response, variables) => {
      if (variables.mode === 'calo' && response.paid) {
        notify({
          title: 'Заказ оплачен',
          description: `Списано ${response.order.amount} CALO`,
          tone: 'success',
        })
      } else {
        notify({
          title: 'Заказ создан',
          description: 'Мы зафиксировали корзину — оплатите заказ в разделе «Заказы».',
          tone: 'success',
        })
      }
      clearCart()
    },
    onError: error => {
      let message = 'Не удалось оформить заказ'
      if (isAxiosError(error)) {
        const data = error.response?.data as any
        if (data) {
          if (typeof data.detail === 'string') {
            message = data.detail
          } else if (typeof data.pay_with_wallet === 'string') {
            message = data.pay_with_wallet
          }
        }
      } else if (error instanceof Error) {
        message = error.message
      }
      notify({ title: 'Ошибка оформления', description: message, tone: 'destructive' })
    },
  })

  const checkoutMode = checkoutMutation.isPending ? checkoutMutation.variables?.mode ?? null : null

  const handleCheckoutRub = useCallback(() => {
    if (!serverCart) {
      notify({
        title: 'Корзина не синхронизирована',
        description: 'Добавьте товары и обновите корзину перед оформлением.',
      })
      return
    }
    checkoutMutation.mutate({ cartId: serverCart.id, mode: 'rub' })
  }, [checkoutMutation, notify, serverCart])

  const handleCheckoutCalo = useCallback(() => {
    if (!serverCart) {
      notify({
        title: 'Корзина не синхронизирована',
        description: 'Добавьте товары и обновите корзину перед оформлением.',
      })
      return
    }
    if (!canPayWithCalo) {
      notify({
        title: 'Недостаточно CaloCoin',
        description: 'Пополните кошелёк или задайте курс CaloCoin в профиле.',
        tone: 'warning',
      })
      return
    }
    checkoutMutation.mutate({ cartId: serverCart.id, mode: 'calo' })
  }, [checkoutMutation, notify, serverCart, canPayWithCalo])

  return {
    cartTotals,
    planTotals,
    insights,
    checkoutMode,
    handleCheckoutRub,
    handleCheckoutCalo,
  }
}
