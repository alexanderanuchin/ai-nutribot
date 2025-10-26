import { NavLink } from 'react-router-dom'
import clsx from 'clsx'

import { MARKET_SECTIONS } from '../constants'

export function MarketSectionNav() {
  return (
    <nav className="flex flex-wrap items-center gap-2" aria-label="Разделы маркета">
      {MARKET_SECTIONS.map(section => (
        <NavLink
          key={section.id}
          to={section.to}
          className={({ isActive }) =>
            clsx(
              'flex min-w-0 flex-col gap-1 rounded-2xl border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:w-auto',
              isActive ? 'border-primary bg-primary/10 text-primary' : 'border-border/60 bg-muted/40 text-foreground hover:bg-muted/60'
            )
          }
        >
          <span className="text-sm font-semibold leading-tight">{section.label}</span>
          <span className="text-xs text-muted-foreground">{section.description}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export default MarketSectionNav