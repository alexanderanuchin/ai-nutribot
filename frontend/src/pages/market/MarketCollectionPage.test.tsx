import { describe, expect, test, vi, beforeAll, afterAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import { MarketCollectionPage } from './MarketCollectionPage'

vi.mock('../../api/market', () => ({
  fetchMarketCollection: vi.fn().mockResolvedValue({
    items: [],
    nextPage: null,
    raw: { count: 0, page: 1, page_size: 12, next: null, previous: null },
  }),
}))

vi.mock('../../features/market/hooks/useMarketRealtime', () => ({
  useMarketRealtime: () => undefined,
}))

const cartTotals = { count: 0, quantity: 0, amount: 0, currency: null }
const planTotals = { count: 0, servings: 0, calories: 0 }

vi.mock('../../features/market/stores/cartStore', () => ({
  useMarketCartStore: (selector?: (state: typeof cartTotals) => unknown) => {
    return selector ? selector(cartTotals) : cartTotals
  },
  selectCartTotals: () => cartTotals,
}))

vi.mock('../../features/market/stores/planStore', () => ({
  useMarketPlanStore: (selector?: (state: typeof planTotals) => unknown) => {
    return selector ? selector(planTotals) : planTotals
  },
  selectPlanTotals: () => planTotals,
}))

describe('MarketCollectionPage mobile filters', () => {
  beforeAll(() => {
    vi.spyOn(window, 'matchMedia').mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }))

    class IntersectionObserverMock {
      constructor() {}
      observe() {}
      disconnect() {}
      unobserve() {}
      takeRecords() { return [] }
    }
    ;(globalThis as any).IntersectionObserver = IntersectionObserverMock

    class ResizeObserverMock {
      constructor() {}
      observe() {}
      disconnect() {}
      unobserve() {}
    }
    ;(globalThis as any).ResizeObserver = ResizeObserverMock
  })

  afterAll(() => {
    vi.restoreAllMocks()
  })

  test('keeps filters sheet closed on initial load', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MarketCollectionPage resource="products" />
        </QueryClientProvider>
      </MemoryRouter>,
    )

    const filterButton = await screen.findAllByRole('button', { name: /фильтры/i })
    expect(filterButton.length).toBeGreaterThan(0)

    await waitFor(() => {
      const openSheet = document.querySelector('[data-radix-dialog-content][data-state="open"]')
      expect(openSheet).toBeNull()
    })

    expect(document.body.style.overflow).not.toBe('hidden')
  })
})
