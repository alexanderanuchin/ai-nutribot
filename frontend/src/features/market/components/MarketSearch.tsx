import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Popover from '@radix-ui/react-popover'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowRightIcon,
  Building2Icon,
  KeyboardIcon,
  SearchIcon,
  SlashIcon,
  SparklesIcon,
  UtensilsCrossedIcon,
  ShoppingBagIcon,
  XIcon,
} from 'lucide-react'
import clsx from 'clsx'

import { searchMarket } from '../../../api/market'
import type {
  MarketQuickFilter,
  MarketResource,
  MarketSearchResponse,
  MarketSearchResultItem,
} from '../../../types/market'
import { useDebouncedValue } from '../../../hooks/useDebouncedValue'
import { Button, Card, Chip, Skeleton } from '../../../components/ui'

export interface MarketSearchHandle {
  openExtended: () => void
}

export interface MarketSearchProps {
  resource: MarketResource
  value: string
  onSubmit: (value: string) => void
  onQuickFilterSelect?: (filter: MarketQuickFilter) => void
}

function isEditableElement(element: EventTarget | null): boolean {
  if (!element || !(element instanceof HTMLElement)) return false
  const tag = element.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || element.isContentEditable
}

function getIconByResource(resource: MarketResource) {
  if (resource === 'recipes') return UtensilsCrossedIcon
  if (resource === 'products') return ShoppingBagIcon
  return Building2Icon
}

function ResultMetrics({ result }: { result: MarketSearchResultItem }) {
  const metrics = result.metrics ?? {}
  if (result.resource === 'products' && typeof metrics.price === 'number') {
    const formatted = new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: (metrics.currency as string) || 'RUB',
      maximumFractionDigits: 0,
    }).format(metrics.price)
    return <span className="text-xs text-muted-foreground">{formatted}</span>
  }
  if (result.resource === 'recipes') {
    const time = metrics.cook_time_minutes ? `${metrics.cook_time_minutes} мин` : null
    const servings = metrics.servings ? `${metrics.servings} порц.` : null
    const difficulty = metrics.difficulty ? String(metrics.difficulty).toUpperCase() : null
    const values = [time, servings, difficulty].filter(Boolean)
    if (values.length === 0) return null
    return <span className="text-xs text-muted-foreground">{values.join(' · ')}</span>
  }
  if (result.resource === 'stores') {
    const city = metrics.city ? String(metrics.city) : null
    const eta = metrics.delivery_eta_minutes ? `${metrics.delivery_eta_minutes} мин` : null
    const values = [city, eta].filter(Boolean)
    if (values.length === 0) return null
    return <span className="text-xs text-muted-foreground">{values.join(' · ')}</span>
  }
  return null
}

function ResultPreview({ result }: { result: MarketSearchResultItem | null }) {
  if (!result) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
        <SparklesIcon className="h-8 w-8" aria-hidden="true" />
        <p>Начните вводить запрос, чтобы увидеть результаты и подробности.</p>
      </div>
    )
  }
  const Icon = getIconByResource(result.resource)
  const preview = result.preview ?? {}
  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="flex min-w-0 flex-col">
          <span className="text-lg font-semibold text-foreground [overflow-wrap:anywhere]">{result.title}</span>
          {result.subtitle ? (
            <span className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{result.subtitle}</span>
          ) : null}
        </div>
      </div>
      {preview.image_url ? (
        <div className="overflow-hidden rounded-3xl border border-border/60">
          <img
            src={String(preview.image_url)}
            alt={result.title}
            loading="lazy"
            className="h-48 w-full object-cover"
          />
        </div>
      ) : null}
      {result.description ? (
        <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-line">{result.description}</p>
      ) : null}
      {result.tags && result.tags.length ? (
        <div className="flex flex-wrap gap-2">
          {result.tags.slice(0, 8).map(tag => (
            <span
              key={tag}
              className="rounded-full bg-muted/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.25em] text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}
      <ResultMetrics result={result} />
    </div>
  )
}

export const MarketSearch = forwardRef<MarketSearchHandle, MarketSearchProps>(function MarketSearch(
  { resource, value, onSubmit, onQuickFilterSelect },
  ref,
) {
  const [inputValue, setInputValue] = useState(value)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [extendedOpen, setExtendedOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const debouncedValue = useDebouncedValue(inputValue, 280)
  const searchScope: 'all' | MarketResource = extendedOpen ? 'all' : resource

  useImperativeHandle(ref, () => ({
    openExtended: () => {
      setPopoverOpen(false)
      setExtendedOpen(true)
    },
  }))

  useEffect(() => {
    setInputValue(value)
  }, [value])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPopoverOpen(false)
        setExtendedOpen(true)
        return
      }
      if (event.key === '/' && !event.metaKey && !event.ctrlKey && !isEditableElement(event.target)) {
        event.preventDefault()
        setPopoverOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const queryEnabled = popoverOpen || extendedOpen
  const { data, isLoading } = useQuery<MarketSearchResponse>({
    queryKey: ['market-search', searchScope, debouncedValue],
    queryFn: async () => searchMarket({ query: debouncedValue, resource: searchScope, limit: extendedOpen ? 18 : 6 }),
    enabled: queryEnabled,
    staleTime: 30_000,
  })

  const resultsLength = data?.results?.length ?? 0

  useEffect(() => {
    setActiveIndex(previousIndex => {
      if (resultsLength === 0) {
        return 0
      }
      if (previousIndex >= resultsLength || previousIndex < 0) {
        return 0
      }
      return previousIndex
    })
  }, [resultsLength])

  const quickFilters = useMemo(() => {
    if (!data?.suggestions?.quick_filters) return []
    if (searchScope === 'all') return data.suggestions.quick_filters
    return data.suggestions.quick_filters.filter(filter => filter.resource === resource)
  }, [data?.suggestions?.quick_filters, resource, searchScope])

  const popular = data?.suggestions?.popular ?? []
  const results = data?.results ?? []
  const selected = results[activeIndex] ?? null

  const handleSubmit = (query: string) => {
    onSubmit(query)
    setPopoverOpen(false)
    setExtendedOpen(false)
  }

  const handleSelectResult = (index: number) => {
    const result = results[index]
    if (!result) return
    setActiveIndex(index)
    handleSubmit(result.title)
  }

  const triggerLabel = value.trim() ? value : 'Поиск по маркету'

  return (
    <>
      <Popover.Root open={popoverOpen} onOpenChange={setPopoverOpen}>
        <Popover.Trigger asChild>
          <button
            type="button"
            className="group flex w-full items-center gap-3 rounded-3xl border border-border/70 bg-card/70 px-4 py-2 text-left shadow-level-1 backdrop-blur transition hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <SearchIcon className="h-4 w-4 text-muted-foreground transition group-hover:text-primary" aria-hidden="true" />
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-sm font-medium text-foreground/90">{triggerLabel}</span>
              <span className="flex items-center gap-2 text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
                <KeyboardIcon className="h-3 w-3" aria-hidden="true" />
                <span>Ctrl/⌘ K</span>
                <SlashIcon className="h-3 w-3" aria-hidden="true" />
              </span>
            </div>
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <AnimatePresence>
            {popoverOpen ? (
              <Popover.Content asChild align="start" sideOffset={12}>
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  transition={{ duration: 0.16, ease: 'easeOut' }}
                  className="z-50 w-[min(540px,90vw)] rounded-3xl border border-border/70 bg-background/95 p-4 shadow-2xl backdrop-blur"
                >
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-2 rounded-2xl border border-border/60 bg-card/70 px-3 py-2">
                      <SearchIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                      <input
                        value={inputValue}
                        onChange={event => setInputValue(event.target.value)}
                        placeholder="Название блюда, ингредиента или магазина"
                        className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
                        autoFocus
                      />
                    </div>
                    {quickFilters.length ? (
                      <div className="flex flex-wrap gap-2">
                        {quickFilters.slice(0, 6).map(filter => (
                          <Chip
                            key={filter.id}
                            tone="muted"
                            onClick={() => {
                              onQuickFilterSelect?.(filter)
                              setPopoverOpen(false)
                            }}
                          >
                            {filter.label}
                          </Chip>
                        ))}
                      </div>
                    ) : null}
                    {popular.length ? (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <SparklesIcon className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="font-semibold uppercase tracking-[0.3em]">Популярное:</span>
                        {popular.slice(0, 4).map(item => (
                          <button
                            key={item}
                            type="button"
                            className="rounded-full bg-muted/20 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.25em] text-muted-foreground transition hover:bg-muted/30"
                            onClick={() => handleSubmit(item)}
                          >
                            {item}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    <div className="flex flex-col gap-2">
                      {isLoading ? (
                        <div className="space-y-2">
                          {Array.from({ length: 3 }).map((_, index) => (
                            <Skeleton key={index} className="h-12 rounded-2xl" />
                          ))}
                        </div>
                      ) : results.length ? (
                        <div className="space-y-2">
                          {results.slice(0, 6).map((result, index) => {
                            const Icon = getIconByResource(result.resource)
                            return (
                              <button
                                key={`${result.resource}-${result.id}`}
                                type="button"
                                onClick={() => handleSelectResult(index)}
                                className="flex w-full items-center gap-3 rounded-2xl border border-transparent bg-transparent px-3 py-2 text-left transition hover:border-border/60 hover:bg-muted/10"
                              >
                                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                  <Icon className="h-5 w-5" aria-hidden="true" />
                                </span>
                                <span className="flex min-w-0 flex-col">
                                  <span className="truncate text-sm font-semibold text-foreground">{result.title}</span>
                                  <ResultMetrics result={result} />
                                </span>
                                <ArrowRightIcon className="ml-auto h-4 w-4 text-muted-foreground" aria-hidden="true" />
                              </button>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-dashed border-border/60 px-4 py-8 text-center text-sm text-muted-foreground">
                          Ничего не найдено. Попробуйте изменить запрос или откройте расширенный поиск.
                        </div>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="justify-between"
                      onClick={() => {
                        setPopoverOpen(false)
                        setExtendedOpen(true)
                      }}
                      trailingIcon={<ArrowRightIcon className="h-4 w-4" aria-hidden="true" />}
                    >
                      Расширенный режим
                    </Button>
                  </div>
                </motion.div>
              </Popover.Content>
            ) : null}
          </AnimatePresence>
        </Popover.Portal>
      </Popover.Root>

      <Dialog.Root open={extendedOpen} onOpenChange={setExtendedOpen}>
        <AnimatePresence>
          {extendedOpen ? (
            <Dialog.Portal forceMount>
              <Dialog.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  className="fixed inset-0 z-[70] bg-black/40 backdrop-blur-sm"
                />
              </Dialog.Overlay>
              <Dialog.Content asChild>
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 24 }}
                  transition={{ duration: 0.2, ease: 'easeOut' }}
                  className="fixed inset-0 z-[71] flex items-start justify-center p-6"
                >
                  <Card
                    elevation={3}
                    className="flex h-[min(80vh,720px)] w-full max-w-[min(1100px,94vw)] overflow-hidden border-border/60 bg-background/95 backdrop-blur"
                  >
                    <div className="flex w-[420px] flex-col border-r border-border/60 bg-card/70">
                      <div className="flex items-center gap-3 border-b border-border/60 px-5 py-4">
                        <SearchIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                        <input
                          value={inputValue}
                          onChange={event => setInputValue(event.target.value)}
                          placeholder="Искать блюда, товары или магазины"
                          className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
                          autoFocus
                        />
                        <Dialog.Close asChild>
                          <button
                            type="button"
                            className="rounded-full border border-transparent p-1 text-muted-foreground transition hover:border-border/50 hover:text-foreground"
                          >
                            <XIcon className="h-4 w-4" aria-hidden="true" />
                          </button>
                        </Dialog.Close>
                      </div>
                      <div className="flex-1 overflow-y-auto px-2 py-4">
                        {isLoading ? (
                          <div className="space-y-3 px-2">
                            {Array.from({ length: 6 }).map((_, index) => (
                              <Skeleton key={index} className="h-12 rounded-2xl" />
                            ))}
                          </div>
                        ) : results.length ? (
                          <ul className="space-y-2 px-2">
                            {results.map((result, index) => {
                              const Icon = getIconByResource(result.resource)
                              const active = index === activeIndex
                              return (
                                <li key={`${result.resource}-${result.id}`}>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setActiveIndex(index)
                                      handleSubmit(result.title)
                                    }}
                                    onMouseEnter={() => setActiveIndex(index)}
                                    className={clsx(
                                      'flex w-full items-center gap-3 rounded-2xl border px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                                      active
                                        ? 'border-primary/60 bg-primary/10 text-primary'
                                        : 'border-transparent bg-transparent hover:border-border/60 hover:bg-muted/10',
                                    )}
                                  >
                                    <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                      <Icon className="h-5 w-5" aria-hidden="true" />
                                    </span>
                                    <span className="flex min-w-0 flex-col">
                                      <span className="truncate text-sm font-semibold">{result.title}</span>
                                      <ResultMetrics result={result} />
                                    </span>
                                  </button>
                                </li>
                              )
                            })}
                          </ul>
                        ) : (
                          <div className="px-6 py-10 text-center text-sm text-muted-foreground">
                            Ничего не найдено. Попробуйте снять часть фильтров или изменить запрос.
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col gap-4 p-6">
                      <ResultPreview result={selected ?? null} />
                    </div>
                  </Card>
                </motion.div>
              </Dialog.Content>
            </Dialog.Portal>
          ) : null}
        </AnimatePresence>
      </Dialog.Root>
    </>
  )
})

MarketSearch.displayName = 'MarketSearch'

export default MarketSearch
