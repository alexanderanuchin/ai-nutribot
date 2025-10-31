import { useState } from 'react'
import { MARKET_FILTERS } from '../constants'
import { MarketFiltersToolbar } from './MarketFilters'

const meta = {
  title: 'Market/FiltersSheet',
  component: MarketFiltersToolbar,
}

export default meta

export const Products = () => {
  const [chips, setChips] = useState<Record<string, boolean>>({})
  const [sort, setSort] = useState('recommended')
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 5000])
  const [rating, setRating] = useState(0)
  const [availability, setAvailability] = useState<'all' | 'available'>('all')

  return (
    <div className="max-w-4xl space-y-4">
      <MarketFiltersToolbar
        layout="laptop"
        resource="products"
        filters={MARKET_FILTERS.products}
        chipValue={chips}
        onToggleChip={(id, active) => setChips(prev => ({ ...prev, [id]: active }))}
        onReset={() => {
          setChips({})
          setSort('recommended')
          setPriceRange([0, 5000])
          setRating(0)
          setAvailability('all')
        }}
        sortValue={sort}
        onSortChange={setSort}
        priceRange={priceRange}
        onPriceRangeChange={setPriceRange}
        ratingValue={rating}
        onRatingChange={setRating}
        availability={availability}
        onAvailabilityChange={setAvailability}
      />
    </div>
  )
}