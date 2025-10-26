import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export interface MarketPlanItem {
  id: number
  title: string
  servings: number
  calories: number
  cookTimeMinutes: number
  imageUrl?: string | null
  tags?: string[] | null
}

export interface MarketPlanState {
  items: Record<number, MarketPlanItem>
  hydrated: boolean
  upsertItem: (item: Omit<MarketPlanItem, 'servings'> & { servings?: number }) => void
  removeItem: (id: number) => void
  clear: () => void
  setHydrated: () => void
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

export const useMarketPlanStore = create<MarketPlanState>()(
  persist(
    set => ({
      items: {},
      hydrated: false,
      upsertItem: item => {
        const servings = item.servings && item.servings > 0 ? item.servings : 1
        set(state => ({
          items: {
            ...state.items,
            [item.id]: {
              ...item,
              servings,
            },
          },
        }))
      },
      removeItem: id => {
        set(state => {
          if (!state.items[id]) return state
          const nextItems = { ...state.items }
          delete nextItems[id]
          return { items: nextItems }
        })
      },
      clear: () => set({ items: {} }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: 'market-plan-v1',
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

export const selectPlanItem = (id: number) => (state: MarketPlanState) => state.items[id] ?? null

export function selectPlanTotals(state: MarketPlanState): {
  count: number
  servings: number
  calories: number
} {
  let count = 0
  let servings = 0
  let calories = 0
  Object.values(state.items).forEach(item => {
    count += 1
    servings += item.servings
    calories += item.servings * item.calories
  })
  return { count, servings, calories }
}