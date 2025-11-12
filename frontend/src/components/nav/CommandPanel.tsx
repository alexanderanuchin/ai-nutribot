import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentType } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { SparklesIcon } from 'lucide-react'
import clsx from 'clsx'
import { useCommandPalette } from '../../hooks/useCommandPalette'
import { useAuth } from '../../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import { PRIMARY_NAVIGATION, SECONDARY_NAVIGATION, COMMAND_ACTIONS, type NavItem } from '../../navigation/schema'
import SearchBox from './SearchBox'

interface CommandEntry {
  id: string
  label: string
  description?: string
  path?: string
  icon?: ComponentType<{ className?: string }>
  section: string
}

function flattenNavItem(item: NavItem, section: string): CommandEntry[] {
  const entries: CommandEntry[] = [
    {
      id: item.id,
      label: item.label,
      description: item.description,
      path: item.path,
      icon: item.icon,
      section,
    },
  ]
  if (item.children) {
    for (const child of item.children) {
      entries.push(...flattenNavItem(child, section))
    }
  }
  return entries
}

function buildCommandEntries(featureFlags: Record<string, boolean | undefined>): CommandEntry[] {
  const entries: CommandEntry[] = []

  for (const item of PRIMARY_NAVIGATION) {
    if (item.featureFlag && featureFlags[item.featureFlag] === false) continue
    entries.push(...flattenNavItem(item, 'Основное'))
  }

  for (const section of SECONDARY_NAVIGATION) {
    if (section.featureFlag && featureFlags[section.featureFlag] === false) continue
    for (const item of section.items) {
      if (item.featureFlag && featureFlags[item.featureFlag] === false) continue
      entries.push(...flattenNavItem(item, section.label))
    }
  }

  for (const action of COMMAND_ACTIONS) {
    entries.push({
      id: action.id,
      label: action.label,
      description: action.description,
      path: action.path,
      section: 'Быстрые действия',
    })
  }

  return entries
}

export function CommandPanel() {
  const { open, closePalette } = useCommandPalette()
  const { user } = useAuth()
  const featureFlags = user?.featureFlags ?? {}
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const entries = useMemo(() => buildCommandEntries(featureFlags), [featureFlags])

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return entries
    return entries.filter(entry => {
      return (
        entry.label.toLowerCase().includes(term) ||
        (entry.description && entry.description.toLowerCase().includes(term)) ||
        entry.section.toLowerCase().includes(term)
      )
    })
  }, [entries, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActiveIndex(0)
    }
  }, [open])

  const filteredCount = filtered.length

  useEffect(() => {
    setActiveIndex(previousIndex => {
      if (filteredCount === 0) {
        return 0
      }
      if (previousIndex >= filteredCount) {
        return filteredCount - 1
      }
      if (previousIndex < 0) {
        return 0
      }
      return previousIndex
    })
  }, [filteredCount])

  useEffect(() => {
    if (listRef.current && filtered.length > 0) {
      const node = listRef.current.querySelectorAll<HTMLButtonElement>('button[data-command-item]')[activeIndex]
      node?.focus()
    }
  }, [activeIndex, filtered])

  const handleKeyNavigation = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex(prev => (prev + 1) % Math.max(filtered.length, 1))
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex(prev => (prev - 1 + Math.max(filtered.length, 1)) % Math.max(filtered.length, 1))
    }
  }

  const handleSelect = (entry: CommandEntry) => {
    if (entry.path) {
      navigate(entry.path)
    }
    closePalette()
  }

  return (
    <Dialog.Root open={open} onOpenChange={isOpen => (!isOpen ? closePalette() : undefined)}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                aria-hidden="true"
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 24 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
                className="fixed inset-x-0 top-[10vh] z-50 mx-auto w-[min(640px,90%)] rounded-3xl border border-border/70 bg-background/95 p-4 shadow-2xl backdrop-blur-xl"
                role="dialog"
                aria-modal="true"
                onKeyDown={handleKeyNavigation}
              >
                <Dialog.Title className="sr-only">Командная палитра</Dialog.Title>
                <Dialog.Description className="sr-only">Быстрые действия и переходы по разделам</Dialog.Description>
                <div className="flex flex-col gap-3">
                  <SearchBox value={query} onChange={setQuery} placeholder="Поиск по разделам" autoFocus />
                  <div
                    ref={listRef}
                    className="max-h-[360px] overflow-y-auto pr-1"
                    role="listbox"
                    aria-label="Результаты"
                  >
                    {filtered.length === 0 ? (
                      <p className="rounded-2xl border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
                        Ничего не найдено. Попробуйте другой запрос.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {filtered.map((entry, index) => {
                          const Icon = entry.icon ?? SparklesIcon
                          const active = index === activeIndex
                          return (
                            <button
                              key={`${entry.section}-${entry.id}`}
                              type="button"
                              data-command-item
                              role="option"
                              aria-selected={active}
                              onClick={() => handleSelect(entry)}
                              className={clsx(
                                'flex w-full items-center gap-3 rounded-2xl border px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                                active
                                  ? 'border-primary/70 bg-primary/10 text-primary'
                                  : 'border-transparent bg-transparent hover:border-border/80 hover:bg-muted/10',
                              )}
                            >
                              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                <Icon className="h-5 w-5" aria-hidden="true" />
                              </span>
                              <span className="flex flex-col">
                                <span className="text-sm font-semibold leading-tight">{entry.label}</span>
                                {entry.description && (
                                  <span className="text-xs text-muted-foreground">{entry.description}</span>
                                )}
                              </span>
                              <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                {entry.section}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export default CommandPanel