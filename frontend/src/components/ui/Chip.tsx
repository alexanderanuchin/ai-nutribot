import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import clsx from 'clsx'

export interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean
  leadingIcon?: ReactNode
  trailingIcon?: ReactNode
  tone?: 'default' | 'primary' | 'success' | 'warning' | 'muted'
}

export const Chip = forwardRef<HTMLButtonElement, ChipProps>(function Chip(
  { className, selected = false, leadingIcon, trailingIcon, tone = 'default', children, ...props },
  ref,
) {
  const toneClass = (() => {
    switch (tone) {
      case 'primary':
        return selected
          ? 'bg-primary text-primary-foreground shadow-level-2'
          : 'bg-primary/10 text-primary hover:bg-primary/16'
      case 'success':
        return selected
          ? 'bg-success text-foreground shadow-level-1'
          : 'bg-success/10 text-success hover:bg-success/16'
      case 'warning':
        return selected
          ? 'bg-warning text-foreground shadow-level-1'
          : 'bg-warning/10 text-warning hover:bg-warning/16'
      case 'muted':
        return selected
          ? 'bg-muted/30 text-foreground'
          : 'bg-muted/15 text-muted-foreground hover:bg-muted/20'
      default:
        return selected
          ? 'bg-card text-foreground shadow-level-1'
          : 'bg-card/80 text-foreground hover:bg-card'
    }
  })()

  return (
    <button
      ref={ref}
      type="button"
      className={clsx(
        'inline-flex min-h-[2.75rem] min-w-[2.75rem] items-center justify-center gap-2 rounded-full border border-border/60 px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        toneClass,
        className,
      )}
      {...props}
    >
      {leadingIcon ? <span className="flex items-center text-base">{leadingIcon}</span> : null}
      <span className="truncate">{children}</span>
      {trailingIcon ? <span className="flex items-center text-base">{trailingIcon}</span> : null}
    </button>
  )
})

export default Chip