import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { MARKET_FILTERS } from '../constants'
import { MarketFiltersSidebar } from './MarketFilters'

describe('MarketFilters', () => {
  beforeAll(() => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    ;(globalThis as unknown as { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver = ResizeObserverMock
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
  })

  afterAll(() => {
    vi.restoreAllMocks()
  })

  it('calls onToggleChip and onSortChange handlers', async () => {
    const user = userEvent.setup()
    const handleToggle = vi.fn()
    const handleSort = vi.fn()

    render(
      <MarketFiltersSidebar
        resource="products"
        filters={MARKET_FILTERS.products}
        chipValue={{}}
        onToggleChip={handleToggle}
        onReset={() => undefined}
        sortValue="recommended"
        onSortChange={handleSort}
        priceRange={[0, 5000]}
        onPriceRangeChange={() => undefined}
        ratingValue={0}
        onRatingChange={() => undefined}
        availability="all"
        onAvailabilityChange={() => undefined}
      />,
    )

    await user.click(screen.getByText(MARKET_FILTERS.products[0].label))
    expect(handleToggle).toHaveBeenCalledWith(MARKET_FILTERS.products[0].id, true)

    await user.click(screen.getByRole('radio', { name: 'Цена ↑' }))
    expect(handleSort).toHaveBeenCalledWith('price_asc')
  })
})