export interface FeedSkeletonProps {
  variant?: 'news' | 'recipes' | 'deals'
}

export function FeedSkeleton({ variant = 'news' }: FeedSkeletonProps) {
  if (variant === 'recipes') {
    return (
      <div className="animate-pulse overflow-hidden rounded-3xl border border-border/50 bg-muted/30 p-4">
        <div className="overflow-hidden rounded-3xl bg-muted/60">
          <div className="aspect-[4/3] w-full bg-muted/50" />
        </div>
        <div className="mt-4 space-y-3">
          <div className="h-4 w-3/4 rounded-full bg-muted/70" />
          <div className="h-3 w-full rounded-full bg-muted/60" />
          <div className="h-3 w-5/6 rounded-full bg-muted/60" />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-16 rounded-2xl bg-muted/50" />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-6 w-20 rounded-full bg-muted/50" />
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="h-11 w-11 rounded-full bg-muted/50" />
          <div className="h-11 flex-1 rounded-full bg-muted/50 sm:w-40 sm:flex-none" />
        </div>
      </div>
    )
  }

  if (variant === 'deals') {
    return (
      <div className="animate-pulse overflow-hidden rounded-3xl border border-border/50 bg-muted/30 p-4">
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="overflow-hidden rounded-2xl bg-muted/60 sm:w-32 sm:flex-shrink-0">
            <div className="aspect-[4/3] w-full bg-muted/50" />
          </div>
          <div className="flex flex-1 flex-col gap-3">
            <div className="h-3 w-2/3 rounded-full bg-muted/60" />
            <div className="h-4 w-5/6 rounded-full bg-muted/70" />
            <div className="flex flex-wrap gap-3">
              <div className="h-6 w-16 rounded-full bg-muted/50" />
              <div className="h-6 w-28 rounded-full bg-muted/50" />
            </div>
            <div className="mt-auto h-3 w-3/4 rounded-full bg-muted/50" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-pulse overflow-hidden rounded-3xl border border-border/50 bg-muted/30 p-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="overflow-hidden rounded-2xl bg-muted/60 sm:w-40 sm:flex-shrink-0">
          <div className="aspect-[4/3] w-full bg-muted/50" />
        </div>
        <div className="flex flex-1 flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            <div className="h-3 w-20 rounded-full bg-muted/50" />
            <div className="h-3 w-16 rounded-full bg-muted/50" />
            <div className="h-3 w-24 rounded-full bg-muted/50" />
          </div>
          <div className="space-y-3">
            <div className="h-4 w-5/6 rounded-full bg-muted/70" />
            <div className="h-3 w-full rounded-full bg-muted/60" />
            <div className="h-3 w-5/6 rounded-full bg-muted/60" />
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-10 rounded-2xl bg-muted/50" />
            ))}
          </div>
          <div className="mt-auto flex flex-wrap gap-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-6 w-16 rounded-full bg-muted/50" />
            ))}
            <div className="h-6 w-24 rounded-full bg-muted/50" />
            <div className="h-9 w-28 rounded-full bg-muted/50 sm:ml-auto" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default FeedSkeleton