import clsx from 'clsx'
import type { HTMLAttributes, ReactNode } from 'react'

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center gap-4 rounded-3xl border border-border/60 bg-card/90 px-6 py-12 text-center shadow-level-1 backdrop-blur-xl',
        className,
      )}
      {...props}
    >
      {icon ? <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/20 text-primary">{icon}</div> : null}
      <div className="flex flex-col gap-1">
        <h3 className="text-title font-semibold text-foreground">{title}</h3>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  )
}

export default EmptyState