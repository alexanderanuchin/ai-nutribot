import { useMemo, useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import { SparklesIcon } from 'lucide-react'
import clsx from 'clsx'
import { PRIMARY_NAVIGATION, SECONDARY_NAVIGATION, type NavItem } from '../../navigation/schema'
import { useActiveRoute } from '../../hooks/useActiveRoute'
import { useAuth } from '../../hooks/useAuth'
import { AppLink } from './AppLink'

export interface SideRailProps {
  onOpenCommand: () => void
}

function isFeatureEnabled(item: NavItem, flags: Record<string, boolean | undefined>) {
  if (!item.featureFlag) return true
  return flags[item.featureFlag] !== false
}

export function SideRail({ onOpenCommand }: SideRailProps) {
  const { isItemActive } = useActiveRoute()
  const { user } = useAuth()
  const featureFlags = user?.featureFlags ?? {}

  const primaryItems = useMemo(() => PRIMARY_NAVIGATION.filter(item => isFeatureEnabled(item, featureFlags)), [featureFlags])
  const sections = useMemo(
    () =>
      SECONDARY_NAVIGATION.map(section => ({
        ...section,
        items: section.items.filter(item => isFeatureEnabled(item, featureFlags)),
        icon: section.items[0]?.icon,
      })).filter(section => section.items.length > 0),
    [featureFlags],
  )

  return (
    <aside
      className="sticky top-0 hidden h-screen w-16 flex-col items-center gap-3 border-r border-border/70 bg-background/95 px-2 py-4 backdrop-blur-xl lg:flex"
      aria-label="Навигация по разделам"
    >
      <div className="flex flex-col items-center gap-2">
        {primaryItems.map(item => {
          const active = isItemActive(item)
          const Icon = item.icon
          return (
            <AppLink
              key={item.id}
              to={item.path ?? '#'}
              aria-current={active ? 'page' : undefined}
              className={clsx(
                'flex h-12 w-12 items-center justify-center rounded-2xl border text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                active
                  ? 'border-primary/70 bg-primary/10 text-primary'
                  : 'border-transparent bg-muted/10 text-muted-foreground hover:border-border/60 hover:bg-muted/20',
              )}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
            </AppLink>
          )
        })}
      </div>
      <div className="mt-6 flex flex-1 flex-col items-center gap-2">
        {sections.map(section => (
          <SectionPopover key={section.id} label={section.label} items={section.items} />
        ))}
      </div>
      <button
        type="button"
        onClick={onOpenCommand}
        className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-soft transition hover:shadow-ring-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        aria-label="AI ассистент"
      >
        <SparklesIcon className="h-5 w-5" aria-hidden="true" />
      </button>
    </aside>
  )
}

interface SectionPopoverProps {
  label: string
  items: NavItem[]
}

function SectionPopover({ label, items }: SectionPopoverProps) {
  const { isItemActive } = useActiveRoute()
  const [open, setOpen] = useState(false)
  const Icon = items[0]?.icon
  const active = items.some(isItemActive)

  const handleOpen = (value: boolean) => setOpen(value)

  return (
    <Popover.Root open={open} onOpenChange={handleOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          onMouseEnter={() => setOpen(true)}
          onFocus={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          onBlur={() => setOpen(false)}
          className={clsx(
            'flex h-12 w-12 items-center justify-center rounded-2xl border text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
            active
              ? 'border-primary/70 bg-primary/10 text-primary'
              : 'border-transparent bg-muted/10 text-muted-foreground hover:border-border/60 hover:bg-muted/20',
          )}
          aria-label={label}
        >
          {Icon ? <Icon className="h-5 w-5" aria-hidden="true" /> : label[0]}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="right"
          align="start"
          sideOffset={12}
          className="z-50 w-60 rounded-2xl border border-border/70 bg-popover/95 p-3 shadow-2xl backdrop-blur-lg"
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</div>
          <div className="flex flex-col gap-1">
            {items.map(item => {
              const itemActive = isItemActive(item)
              const ItemIcon = item.icon
              return (
                <AppLink
                  key={item.id}
                  to={item.path ?? '#'}
                  className={clsx(
                    'flex items-center gap-3 rounded-xl px-2 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                    itemActive ? 'bg-primary/10 text-primary' : 'hover:bg-muted/10',
                  )}
                  aria-current={itemActive ? 'page' : undefined}
                  onClick={() => setOpen(false)}
                >
                  {ItemIcon && (
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/20 text-muted-foreground">
                      <ItemIcon className="h-4 w-4" aria-hidden="true" />
                    </span>
                  )}
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground">{item.label}</span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </div>
                </AppLink>
              )
            })}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}

export default SideRail