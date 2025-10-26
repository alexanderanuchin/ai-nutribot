import { NavLink } from 'react-router-dom'
import clsx from 'clsx'

import { MARKET_SECTIONS } from '../constants'

export function MarketSectionNav() {
  return (
    <nav
      className="grid grid-cols-1 gap-2 rounded-3xl bg-muted/40 p-1.5 shadow-soft sm:grid-cols-2 lg:grid-cols-4"
      aria-label="Разделы маркета"
    >
      {MARKET_SECTIONS.map(section => (
        <NavLink
          key={section.id}
          to={section.to}
          end={section.to === '/market'}
          className={({ isActive }) =>
            clsx(
              'group flex min-h-[2.75rem] min-w-0 flex-col gap-1 rounded-2xl px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              isActive
                ? 'bg-background text-foreground shadow-soft ring-1 ring-primary/50'
                : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          <span className="truncate text-sm font-semibold leading-snug">{section.label}</span>
          <span className="truncate text-[11px] leading-none text-muted-foreground">{section.description}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export default MarketSectionNav