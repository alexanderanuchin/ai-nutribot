import { useMemo, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import clsx from 'clsx'

import type { MarketFilterDefinition } from '../constants'
import { useMediaQuery } from '../../../hooks/useMediaQuery'

export interface MarketFiltersProps {
  filters: MarketFilterDefinition[]
  value: Record<string, boolean>
  onToggle: (id: string, active: boolean) => void
  onReset?: () => void
}

export function MarketFilters({ filters, value, onToggle, onReset }: MarketFiltersProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const activeCount = useMemo(() => Object.values(value).filter(Boolean).length, [value])
  const [open, setOpen] = useState(false)

  if (filters.length === 0) return null

  if (isDesktop) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {filters.map(filter => {
          const active = Boolean(value[filter.id])
          return (
            <button
              key={filter.id}
              type="button"
              onClick={() => onToggle(filter.id, !active)}
              className={clsx(
                'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                active
                  ? 'bg-primary text-primary-foreground shadow-soft'
                  : 'bg-muted/60 text-foreground hover:bg-muted'
              )}
            >
              {filter.label}
            </button>
          )
        })}
        {activeCount > 0 && onReset ? (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1 rounded-full border border-border/60 px-3 py-2 text-xs font-semibold text-muted-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Сбросить
          </button>
        ) : null}
      </div>
    )
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full border border-border/60 px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Фильтры
          {activeCount > 0 ? (
            <span className="inline-flex min-h-[1.5rem] min-w-[1.5rem] items-center justify-center rounded-full bg-primary/10 px-2 text-xs font-semibold text-primary">
              {activeCount}
            </span>
          ) : null}
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-x-4 bottom-4 z-50 rounded-3xl border border-border/70 bg-background/98 p-4 shadow-2xl">
          <Dialog.Title className="text-base font-semibold text-foreground">Фильтры</Dialog.Title>
          <Dialog.Description className="mt-1 text-xs text-muted-foreground">
            Выберите категории и предпочтения
          </Dialog.Description>
          <div className="mt-4 flex flex-col gap-3">
            {filters.map(filter => {
              const active = Boolean(value[filter.id])
              return (
                <button
                  key={filter.id}
                  type="button"
                  onClick={() => onToggle(filter.id, !active)}
                  className={clsx(
                    'flex items-center justify-between rounded-2xl border px-3 py-3 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                    active ? 'border-primary bg-primary/10 text-primary' : 'border-border/60 bg-muted/40 text-foreground'
                  )}
                >
                  <span className="flex flex-col items-start gap-0.5 text-left">
                    {filter.label}
                    {filter.description ? (
                      <span className="text-xs font-normal text-muted-foreground">{filter.description}</span>
                    ) : null}
                  </span>
                  <span
                    className={clsx(
                      'inline-flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-bold',
                      active
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-border/80 bg-background text-muted-foreground'
                    )}
                    aria-hidden="true"
                  >
                    {active ? '✓' : ''}
                  </span>
                </button>
              )
            })}
          </div>
          <div className="mt-4 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => {
                onReset?.()
                setOpen(false)
              }}
              className="text-sm font-semibold text-muted-foreground"
            >
              Сбросить
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              Готово
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export default MarketFilters