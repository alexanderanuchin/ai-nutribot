import type { ReactNode } from 'react'

export interface MarketPageHeaderProps {
  title: string
  description?: string
  action?: ReactNode
  children?: ReactNode
}

export function MarketPageHeader({ title, description, action, children }: MarketPageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 rounded-3xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-6 text-foreground shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-2">
          <h1 className="text-2xl font-bold leading-tight tracking-tight text-foreground [overflow-wrap:anywhere]">{title}</h1>
          {description ? <p className="max-w-2xl text-sm text-muted-foreground [overflow-wrap:anywhere]">{description}</p> : null}
        </div>
        {action ? <div className="flex-shrink-0">{action}</div> : null}
      </div>
      {children ? <div className="flex flex-col gap-3">{children}</div> : null}
    </header>
  )
}

export default MarketPageHeader