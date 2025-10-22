import clsx from 'clsx'
import type { FeedTab } from '../../../types/feed'
import { FEED_TABS } from '../constants'

export interface FeedTabsProps {
  active: FeedTab
  onChange: (tab: FeedTab) => void
  badges?: Partial<Record<FeedTab, number>>
}

export function FeedTabs({ active, onChange, badges }: FeedTabsProps) {
  return (
    <div className="grid grid-cols-3 gap-2 rounded-3xl bg-muted/40 p-1.5 shadow-soft">
      {FEED_TABS.map(tab => {
        const isActive = tab.id === active
        const badge = badges?.[tab.id]
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={clsx(
              'group flex min-h-[2.75rem] min-w-0 flex-col gap-1 rounded-2xl px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              isActive
                ? 'bg-background text-foreground shadow-soft ring-1 ring-primary/50'
                : 'text-muted-foreground hover:text-foreground'
            )}
            aria-pressed={isActive}
          >
            <div className="truncate text-sm font-semibold leading-snug">{tab.label}</div>
            <div className="flex min-w-0 items-center gap-2 text-[11px] leading-none text-muted-foreground">
              <span className="truncate">{tab.subtitle}</span>
              {badge ? (
                <span className="inline-flex min-h-[1.25rem] min-w-[1.25rem] items-center justify-center truncate rounded-full bg-primary/15 px-2 text-[10px] font-semibold text-primary">
                  +{badge}
                </span>
              ) : null}
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default FeedTabs