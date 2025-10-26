import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type MarketCartItemKind = 'product' | 'bundle'

export interface MarketCartItem {
  kind: MarketCartItemKind
  id: number
  title: string
  quantity: number
  price: number
  currency: string
  imageUrl?: string | null
  unit?: string | null
}

export interface MarketCartState {
  items: Record<string, MarketCartItem>
  hydrated: boolean
  addItem: (item: Omit<MarketCartItem, 'quantity'> & { quantity?: number }) => void
  increment: (kind: MarketCartItemKind, id: number) => void
  decrement: (kind: MarketCartItemKind, id: number) => void
  removeItem: (kind: MarketCartItemKind, id: number) => void
  setQuantity: (item: Omit<MarketCartItem, 'quantity'>, quantity: number) => void
  clear: () => void
  setHydrated: () => void
}

function makeKey(kind: MarketCartItemKind, id: number): string {
  return `${kind}:${id}`
}

function getStorage(): Storage {
  if (typeof window === 'undefined') {
    return {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
      clear: () => undefined,
      key: () => null,
      length: 0,
    }
  }
  return window.localStorage
}

export const useMarketCartStore = create<MarketCartState>()(
  persist(
    set => ({
      items: {},
      hydrated: false,
      addItem: item => {
        const quantity = item.quantity && item.quantity > 0 ? item.quantity : 1
        const key = makeKey(item.kind, item.id)
        set(state => {
          const existing = state.items[key]
          const nextQuantity = existing ? existing.quantity + quantity : quantity
          return {
            items: {
              ...state.items,
              [key]: {
                ...item,
                quantity: nextQuantity,
              },
            },
          }
        })
      },
      increment: (kind, id) => {
        const key = makeKey(kind, id)
        set(state => {
          const existing = state.items[key]
          if (!existing) return state
          return {
            items: {
              ...state.items,
              [key]: {
                ...existing,
                quantity: existing.quantity + 1,
              },
            },
          }
        })
      },
      decrement: (kind, id) => {
        const key = makeKey(kind, id)
        set(state => {
          const existing = state.items[key]
          if (!existing) return state
          const nextQuantity = existing.quantity - 1
          if (nextQuantity <= 0) {
            const nextItems = { ...state.items }
            delete nextItems[key]
            return { items: nextItems }
          }
          return {
            items: {
              ...state.items,
              [key]: {
                ...existing,
                quantity: nextQuantity,
              },
            },
          }
        })
      },
      removeItem: (kind, id) => {
        const key = makeKey(kind, id)
        set(state => {
          if (!state.items[key]) return state
          const nextItems = { ...state.items }
          delete nextItems[key]
          return { items: nextItems }
        })
      },
      setQuantity: (item, quantity) => {
        const key = makeKey(item.kind, item.id)
        set(state => {
          if (quantity <= 0) {
            if (!state.items[key]) return state
            const nextItems = { ...state.items }
            delete nextItems[key]
            return { items: nextItems }
          }
          const existing = state.items[key]
          return {
            items: {
              ...state.items,
              [key]: {
                ...(existing ?? item),
                quantity,
              },
            },
          }
        })
      },
      clear: () => set({ items: {} }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: 'market-cart-v1',
      storage: createJSONStorage(getStorage),
      partialize: state => ({ items: state.items }),
      onRehydrateStorage: () => state => {
        const markHydrated = () => state?.setHydrated()
        if (typeof queueMicrotask === 'function') {
          queueMicrotask(markHydrated)
          return
        }
        Promise.resolve().then(markHydrated)
      },
    }
  )
)

export function selectCartItem(kind: MarketCartItemKind, id: number) {
  const key = makeKey(kind, id)
  return (state: MarketCartState) => state.items[key] ?? null
}

export function selectCartQuantity(kind: MarketCartItemKind, id: number) {
  return (state: MarketCartState) => {
    const item = state.items[makeKey(kind, id)]
    return item?.quantity ?? 0
  }
}

export function selectCartTotals(state: MarketCartState): {
  count: number
  quantity: number
  amount: number
  currency: string | null
} {
  let count = 0
  let quantity = 0
  let amount = 0
  let currency: string | null = null
  Object.values(state.items).forEach(item => {
    count += 1
    quantity += item.quantity
    amount += item.quantity * item.price
    if (!currency && item.currency) {
      currency = item.currency
    }
  })
  return { count, quantity, amount, currency }
}