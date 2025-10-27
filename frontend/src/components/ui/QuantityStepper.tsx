import { MinusIcon, PlusIcon } from 'lucide-react'
import clsx from 'clsx'

interface QuantityStepperProps {
  value: number
  min?: number
  max?: number
  step?: number
  onChange: (value: number) => void
  disabled?: boolean
  className?: string
}

export function QuantityStepper({
  value,
  min = 1,
  max = Number.MAX_SAFE_INTEGER,
  step = 1,
  onChange,
  disabled = false,
  className,
}: QuantityStepperProps) {
  const handleDecrease = () => {
    if (disabled) return
    const next = Math.max(min, value - step)
    if (next !== value) {
      onChange(next)
    }
  }

  const handleIncrease = () => {
    if (disabled) return
    const next = Math.min(max, value + step)
    if (next !== value) {
      onChange(next)
    }
  }

  return (
    <div className={clsx('inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/90 px-1.5 py-1 shadow-level-1', className)}>
      <button
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-full text-foreground transition hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onClick={handleDecrease}
        disabled={disabled || value <= min}
        aria-label="Уменьшить количество"
      >
        <MinusIcon className="h-4 w-4" aria-hidden="true" />
      </button>
      <span className="min-w-[2ch] text-center text-sm font-semibold text-foreground" aria-live="polite">
        {value}
      </span>
      <button
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-full text-foreground transition hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onClick={handleIncrease}
        disabled={disabled || value >= max}
        aria-label="Увеличить количество"
      >
        <PlusIcon className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  )
}

export default QuantityStepper