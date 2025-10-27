import clsx from 'clsx'
import type { HTMLAttributes } from 'react'

export interface ShimmerProps extends HTMLAttributes<HTMLDivElement> {
  intensity?: number
}

export function Shimmer({ className, intensity = 0.45, ...props }: ShimmerProps) {
  return (
    <div
      className={clsx('relative overflow-hidden rounded-xl bg-muted/10', className)}
      {...props}
    >
      <div
        className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-white/60 to-transparent"
        style={{ opacity: intensity }}
      />
    </div>
  )
}

export default Shimmer