import clsx from 'clsx'

export interface MarketListSkeletonProps {
  variant: 'recipes' | 'products' | 'stores'
  count?: number
}

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={clsx('animate-pulse rounded-2xl bg-muted/60', className)} />
}

export function MarketListSkeleton({ variant, count = 6 }: MarketListSkeletonProps) {
  const items = Array.from({ length: count })

  if (variant === 'stores') {
    return (
      <div className="flex flex-col gap-4">
        {items.map((_, index) => (
          <div key={index} className="flex flex-col gap-4 rounded-3xl border border-border/60 bg-background/80 p-4 shadow-soft sm:flex-row">
            <SkeletonBlock className="h-36 w-full sm:h-40 sm:w-40" />
            <div className="flex flex-1 flex-col gap-3">
              <SkeletonBlock className="h-6 w-1/2" />
              <SkeletonBlock className="h-4 w-full" />
              <SkeletonBlock className="h-4 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'products') {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((_, index) => (
          <div key={index} className="flex flex-col gap-3 rounded-3xl border border-border/60 bg-background/80 p-4 shadow-soft">
            <SkeletonBlock className="aspect-square w-full" />
            <SkeletonBlock className="h-5 w-3/4" />
            <SkeletonBlock className="h-4 w-1/2" />
            <SkeletonBlock className="h-4 w-2/3" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((_, index) => (
        <div key={index} className="flex flex-col gap-3 rounded-3xl border border-border/60 bg-background/80 p-4 shadow-soft">
          <SkeletonBlock className="aspect-[4/3] w-full" />
          <SkeletonBlock className="h-5 w-3/4" />
          <SkeletonBlock className="h-4 w-2/3" />
          <SkeletonBlock className="h-4 w-1/2" />
        </div>
      ))}
    </div>
  )
}

export default MarketListSkeleton