import { describe, expect, test, vi, beforeAll, afterAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import { fetchMarketCollection } from '../../api/market'
import { MarketCollectionPage } from './MarketCollectionPage'

vi.mock('../../api/market', () => ({
  fetchMarketCollection: vi.fn().mockResolvedValue({
    items: [],
    nextPage: null,
    raw: { count: 0, page: 1, page_size: 12, next: null, previous: null },
  }),
}))

vi.mock('../../features/market/hooks/useMarketEvents', () => ({
  useMarketEvents: () => undefined,
}))

const cartTotals = { count: 0, quantity: 0, amount: 0, currency: null }
const cartStoreState = {
  ...cartTotals,
  items: {},
  hydrated: true,
  serverCart: null as { id: number; storeId: number; currency: string } | null,
  clear: vi.fn(),
  setServerCart: vi.fn(),
}
const planTotals = { count: 0, servings: 0, calories: 0 }

vi.mock('../../features/market/stores/cartStore', () => ({
  useMarketCartStore: (selector?: (state: typeof cartStoreState) => unknown) => {
    return selector ? selector(cartStoreState) : cartStoreState
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

describe('MarketCollectionPage desktop filters', () => {
  beforeAll(() => {
    vi.spyOn(window, 'matchMedia').mockImplementation(query => ({
      matches: query === '(min-width: 1024px)',
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }))

    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    ;(globalThis as any).ResizeObserver = ResizeObserverMock

    class IntersectionObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return []
      }
    }
    ;(globalThis as any).IntersectionObserver = IntersectionObserverMock
  })

  afterAll(() => {
    vi.restoreAllMocks()
  })

  test('applies quick filters and rating to collection requests', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })
    const user = userEvent.setup()
    const fetchMock = vi.mocked(fetchMarketCollection)

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MarketCollectionPage resource="recipes" />
        </QueryClientProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    fetchMock.mockClear()

    await user.click(await screen.findByRole('button', { name: 'Больше белка' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    let lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters).toMatchObject({ min_protein: 25 })

    fetchMock.mockClear()
    await user.click(screen.getByRole('button', { name: 'До 300 ₽' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters).toMatchObject({ min_protein: 25, max_price: 300 })

    fetchMock.mockClear()
    const ratingToggle = screen.getByRole('radio', { name: /4\+/ })
    await user.click(ratingToggle)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters).toMatchObject({ min_protein: 25, max_price: 300, min_rating: 4 })
  })

  test('sends ordering aliases for stores sort options', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })
    const user = userEvent.setup()
    const fetchMock = vi.mocked(fetchMarketCollection)

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MarketCollectionPage resource="stores" />
        </QueryClientProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    let lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters?.ordering).toBe('-rating')

    fetchMock.mockClear()
    await user.click(screen.getByRole('radio', { name: 'Доставка' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters?.ordering).toBe('eta')

    fetchMock.mockClear()
    await user.click(screen.getByRole('radio', { name: 'Новые' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    lastCall = fetchMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.filters?.ordering).toBe('-freshness')
  })
})
