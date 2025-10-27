import clsx from 'clsx'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: 'muted' | 'primary' | 'success' | 'warning' | 'outline'
  leadingIcon?: React.ReactNode
}

export function Badge({ className, children, tone = 'muted', leadingIcon, ...props }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex min-h-[2rem] items-center justify-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]',
        tone === 'muted' && 'bg-muted/15 text-muted-foreground',
        tone === 'primary' && 'bg-primary/10 text-primary',
        tone === 'success' && 'bg-success/10 text-success',
        tone === 'warning' && 'bg-warning/12 text-warning',
        tone === 'outline' && 'border border-border/70 text-muted-foreground',
        className,
      )}
      {...props}
    >
      {leadingIcon ? <span className="flex items-center text-base">{leadingIcon}</span> : null}
      <span className="truncate">{children}</span>
    </span>
  )
}

export default Badge