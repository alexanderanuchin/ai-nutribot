export interface FeedSkeletonProps {
  variant?: 'news' | 'recipes' | 'deals'
}

export function FeedSkeleton({ variant = 'news' }: FeedSkeletonProps) {
  return (
    <div className="animate-pulse rounded-3xl border border-border/50 bg-muted/30 p-4">
      <div className="flex items-start gap-4">
        {variant !== 'recipes' ? <div className="hidden h-20 w-20 rounded-2xl bg-muted sm:block" /> : null}
        <div className="flex-1 space-y-3">
          <div className="h-3 w-1/3 rounded-full bg-muted" />
          <div className="h-4 w-3/4 rounded-full bg-muted" />
          <div className="h-4 w-2/4 rounded-full bg-muted" />
          <div className="flex gap-2">
            <div className="h-6 w-16 rounded-full bg-muted" />
            <div className="h-6 w-24 rounded-full bg-muted" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default FeedSkeleton