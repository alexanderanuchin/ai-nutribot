import { useState } from 'react'
import { MARKET_FILTERS } from '../constants'
import { MarketFiltersMobileSheet, MarketFiltersSidebar } from './MarketFilters'

const meta = {
  title: 'Market/Filters',
  component: MarketFiltersSidebar,
}

export default meta

export const Products = () => {
  const [chips, setChips] = useState<Record<string, boolean>>({})
  const [sort, setSort] = useState('recommended')
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 5000])
  const [rating, setRating] = useState(0)
  const [availability, setAvailability] = useState<'all' | 'available'>('all')

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex flex-col gap-4">
        <MarketFiltersMobileSheet
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
      <MarketFiltersSidebar
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