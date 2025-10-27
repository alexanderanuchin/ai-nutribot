import clsx from 'clsx'
import type { HTMLAttributes } from 'react'

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  shimmer?: boolean
}

export function Skeleton({ className, shimmer = true, ...props }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl bg-muted/20',
        shimmer && 'after:absolute after:inset-0 after:-translate-x-full after:animate-[shimmer_1.4s_infinite] after:bg-gradient-to-r after:from-transparent after:via-white/30 after:to-transparent',
        className,
      )}
      {...props}
    />
  )
}

export default Skeleton