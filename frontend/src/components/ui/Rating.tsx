import { StarIcon } from 'lucide-react'
import clsx from 'clsx'

interface RatingProps {
  value: number
  count?: number
  className?: string
  size?: 'sm' | 'md'
}

const STARS = [1, 2, 3, 4, 5]

export function Rating({ value, count, className, size = 'md' }: RatingProps) {
  const clamped = Math.max(0, Math.min(5, value))
  return (
    <div className={clsx('flex items-center gap-1 text-warning', className)} aria-label={`Рейтинг ${clamped} из 5`}>
      {STARS.map(star => {
        const filled = clamped >= star
        const half = !filled && clamped + 0.5 >= star
        return (
          <span key={star} className="relative inline-flex">
            <StarIcon
              className={clsx(size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4', 'opacity-60 text-warning')}
              aria-hidden="true"
              strokeWidth={1.6}
              fill={filled ? 'currentColor' : 'transparent'}
            />
            {half ? (
              <span className="absolute inset-y-0 left-0 w-1/2 overflow-hidden text-warning">
                <StarIcon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} fill="currentColor" strokeWidth={0} />
              </span>
            ) : null}
          </span>
        )
      })}
      {count != null ? (
        <span className="ml-2 text-xs text-muted-foreground">{count.toLocaleString('ru-RU')}</span>
      ) : null}
    </div>
  )
}

export default Rating