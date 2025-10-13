import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { CoinsIcon, SparklesIcon } from 'lucide-react'
import clsx from 'clsx'
import { useWallet } from '../../hooks/useWallet'
import { AppLink } from './AppLink'
import { useSafeArea } from '../../hooks/useSafeArea'

export interface WalletBadgeProps {
  className?: string
}

function formatNumber(value: number) {
  return value.toLocaleString('ru-RU')
}

export function WalletBadge({ className }: WalletBadgeProps) {
  const [open, setOpen] = useState(false)
  const { data, isLoading } = useWallet()
  const safeArea = useSafeArea({ inset: 20, edges: ['bottom', 'left', 'right'] })

  const stars = data?.balance.stars ?? 0
  const calo = data?.balance.calo ?? 0

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={clsx(
            'group flex shrink-0 items-center gap-2 rounded-full border border-border/60 bg-background/80 px-2 py-1.5 text-sm shadow-soft transition hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:px-3',
            className,
          )}
          aria-label="Открыть кошелёк"
        >
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-primary md:hidden">
            <SparklesIcon className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="hidden items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs font-semibold text-primary md:flex">
            <SparklesIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {isLoading ? <span className="animate-pulse">•••</span> : formatNumber(stars)}
          </span>
          <span className="hidden items-center gap-1 rounded-full bg-accent/10 px-2 py-1 text-xs font-semibold text-accent-foreground md:flex">
            <CoinsIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {isLoading ? <span className="animate-pulse">•••</span> : formatNumber(calo)}
          </span>
          <span className="sr-only">
            Баланс:{' '}
            {isLoading
              ? 'загрузка'
              : `звёзды — ${formatNumber(stars)}, calo — ${formatNumber(calo)}`}
          </span>
        </button>
      </Dialog.Trigger>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-50 bg-black/40"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                aria-hidden="true"
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                className="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-3xl border border-border/80 bg-background/98 shadow-2xl"
                style={safeArea}
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                role="dialog"
              >
                <Dialog.Title className="sr-only">Кошелёк</Dialog.Title>
                <Dialog.Description className="sr-only">Баланс и последние операции кошелька</Dialog.Description>
                <div className="mx-auto mb-4 mt-2 h-1.5 w-12 rounded-full bg-muted" aria-hidden="true" />
                <div className="px-6 pb-6">
                  <div className="mb-5 flex items-center justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">Кошелёк</h2>
                      <p className="text-xs text-muted-foreground">Баланс обновлён: {data?.balance.updatedAt ? new Date(data.balance.updatedAt).toLocaleTimeString() : 'только что'}</p>
                    </div>
                    <AppLink
                      to="/billing"
                      className="rounded-full border border-primary/60 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary transition hover:bg-primary/20"
                      onClick={() => setOpen(false)}
                    >
                      Монетизация
                    </AppLink>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-primary/40 bg-primary/5 p-4">
                      <div className="flex items-center justify-between text-xs text-primary">
                        Stars
                        <SparklesIcon className="h-4 w-4" aria-hidden="true" />
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-primary">{isLoading ? '•••' : formatNumber(stars)}</div>
                    </div>
                    <div className="rounded-2xl border border-accent/60 bg-accent/10 p-4">
                      <div className="flex items-center justify-between text-xs text-accent-foreground">
                        Calo
                        <CoinsIcon className="h-4 w-4" aria-hidden="true" />
                      </div>
                      <div className="mt-2 text-2xl font-semibold text-accent-foreground">{isLoading ? '•••' : formatNumber(calo)}</div>
                    </div>
                  </div>
                  {data?.starsPurchaseBlocked && (
                    <div className="mt-4 rounded-2xl border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-xs font-medium text-amber-900 dark:text-amber-200">
                      Пополнение Stars временно недоступно: Telegram ограничил покупки в вашем регионе.
                    </div>
                  )}
                  <div className="mt-6">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Недавние операции</h3>
                    <div className="mt-2 space-y-2">
                      {isLoading
                        ? Array.from({ length: 3 }).map((_, index) => (
                            <div
                              key={index}
                              className="h-12 w-full animate-pulse rounded-xl border border-border/60 bg-muted/10"
                              aria-hidden="true"
                            />
                          ))
                        : data?.transactions.map(item => (
                            <div
                              key={item.id}
                              className="flex items-center gap-3 rounded-xl border border-border/60 bg-background/80 px-3 py-2"
                            >
                              <span
                                className={clsx(
                                  'flex h-9 w-9 items-center justify-center rounded-xl text-sm font-semibold',
                                  item.currency === 'stars'
                                    ? 'bg-primary/10 text-primary'
                                    : 'bg-accent/10 text-accent-foreground',
                                )}
                              >
                                {item.currency === 'stars' ? '★' : '₵'}
                              </span>
                              <div className="flex flex-col text-left text-sm">
                                <span className="font-semibold text-foreground">{item.title}</span>
                                <span className="text-xs text-muted-foreground">
                                  {new Date(item.timestamp).toLocaleString('ru-RU', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    day: '2-digit',
                                    month: 'short',
                                  })}
                                </span>
                              </div>
                              <span className={clsx('ml-auto text-sm font-semibold', item.direction === 'in' ? 'text-accent-foreground' : 'text-primary')}>
                                {item.direction === 'in' ? '+' : '-'}{formatNumber(item.amount)}
                              </span>
                            </div>
                          ))}
                    </div>
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

export default WalletBadge