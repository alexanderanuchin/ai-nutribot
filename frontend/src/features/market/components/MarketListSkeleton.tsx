import clsx from 'clsx'

import { Card, Skeleton } from '../../../components/ui'

export interface MarketListSkeletonProps {
  variant: 'recipes' | 'products' | 'stores'
  count?: number
}

export function MarketListSkeleton({ variant, count = 6 }: MarketListSkeletonProps) {
  const items = Array.from({ length: count })

  if (variant === 'stores') {
    return (
      <div className="flex flex-col gap-4">
        {items.map((_, index) => (
          <Card key={index} className="flex flex-col gap-4 sm:flex-row" elevation={1}>
            <Skeleton className="h-36 w-full sm:h-40 sm:w-40" />
            <div className="flex flex-1 flex-col gap-3">
              <Skeleton className="h-6 w-1/2" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </Card>
        ))}
      </div>
    )
  }

  const gridClass = clsx('grid gap-4', variant === 'products' ? 'sm:grid-cols-2 xl:grid-cols-3' : 'sm:grid-cols-2 xl:grid-cols-3')

  return (
    <div className={gridClass}>
      {items.map((_, index) => (
        <Card key={index} className="flex flex-col gap-3" elevation={1}>
          <Skeleton className={variant === 'products' ? 'aspect-square w-full' : 'aspect-[4/3] w-full'} />
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </Card>
      ))}
    </div>
  )
}

export default MarketListSkeleton