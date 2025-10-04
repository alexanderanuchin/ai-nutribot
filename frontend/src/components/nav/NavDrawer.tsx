import { useMemo } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronRightIcon, ExternalLinkIcon, SparklesIcon } from 'lucide-react'
import clsx from 'clsx'
import { PRIMARY_NAVIGATION, SECONDARY_NAVIGATION, COMMAND_ACTIONS, type NavItem } from '../../navigation/schema'
import { useAuth } from '../../hooks/useAuth'
import { useActiveRoute } from '../../hooks/useActiveRoute'
import { useSafeArea } from '../../hooks/useSafeArea'
import { AppLink } from './AppLink'

export interface NavDrawerProps {
  open: boolean
  onOpenChange: (value: boolean) => void
  onLogout?: () => void
}

function isFeatureEnabled(item: NavItem, flags: Record<string, boolean | undefined>): boolean {
  if (!item.featureFlag) return true
  return flags[item.featureFlag] !== false
}

export function NavDrawer({ open, onOpenChange, onLogout }: NavDrawerProps) {
  const { user, logout } = useAuth()
  const featureFlags = user?.featureFlags ?? {}
  const { isItemActive, isSectionActive } = useActiveRoute()
  const safeArea = useSafeArea({ inset: 20 })

  const primaryItems = useMemo(() => PRIMARY_NAVIGATION.filter(item => isFeatureEnabled(item, featureFlags)), [featureFlags])

  const sections = useMemo(
    () =>
      SECONDARY_NAVIGATION.map(section => ({
        ...section,
        items: section.items.filter(item => isFeatureEnabled(item, featureFlags)),
      })).filter(section => section.items.length > 0),
    [featureFlags],
  )

  const handleLogout = () => {
    logout()
    onLogout?.()
    onOpenChange(false)
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
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
              <motion.aside
                className="fixed inset-y-0 left-0 z-50 flex w-[min(88vw,360px)] flex-col rounded-r-3xl border border-border/80 bg-background/98 shadow-2xl backdrop-blur-xl"
                style={safeArea}
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.12}
                onDragEnd={(_, info) => {
                  if (info.velocity.x > 500 || info.offset.x > 160) {
                    onOpenChange(false)
                  }
                }}
                role="dialog"
              >
                <Dialog.Title className="sr-only">Меню навигации</Dialog.Title>
                <Dialog.Description className="sr-only">Выберите раздел или действие</Dialog.Description>
                <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 pb-6">
                  <div className="mt-2 flex items-center gap-3 rounded-2xl border border-border/70 bg-muted/10 p-4">
                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/15 text-lg font-semibold text-primary">
                      {user?.avatarUrl ? (
                        <img
                          src={user.avatarUrl}
                          alt={user.fullName}
                          className="h-full w-full rounded-2xl object-cover"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        (user?.fullName ?? 'Гость')
                          .split(' ')
                          .filter(Boolean)
                          .map(part => part[0]?.toUpperCase())
                          .slice(0, 2)
                          .join('') || 'AI'
                      )}
                    </span>
                    <div className="flex flex-col">
                      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{user?.mode ?? 'Гость'}</span>
                      <span className="text-lg font-semibold text-foreground">{user?.fullName ?? 'Гость'}</span>
                      <span className="text-xs text-muted-foreground">{user?.email ?? 'Подключитесь, чтобы видеть данные'}</span>
                    </div>
                  </div>

                  <nav className="space-y-3" aria-label="Основная навигация">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Главное</h3>
                    <div className="flex flex-col gap-2">
                      {primaryItems.map(item => {
                        const active = isItemActive(item)
                        const Icon = item.icon
                        return (
                          <AppLink
                            key={item.id}
                            to={item.path ?? '#'}
                            onClick={() => onOpenChange(false)}
                            className={clsx(
                              'flex items-center gap-3 rounded-2xl border px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                              active
                                ? 'border-primary/70 bg-primary/10 text-primary'
                                : 'border-transparent bg-transparent hover:border-border/70 hover:bg-muted/10',
                            )}
                            aria-current={active ? 'page' : undefined}
                          >
                            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                              <Icon className="h-4 w-4" aria-hidden="true" />
                            </span>
                            <span>{item.label}</span>
                            <ChevronRightIcon className="ml-auto h-4 w-4 text-muted-foreground" aria-hidden="true" />
                          </AppLink>
                        )
                      })}
                    </div>
                  </nav>

                  <nav className="space-y-3" aria-label="Категории">
                    {sections.map(section => (
                      <div key={section.id} className="space-y-2">
                        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          {section.label}
                          {isSectionActive(section) && <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] text-primary">активно</span>}
                        </div>
                        <div className="flex flex-col gap-1">
                          {section.items.map(item => {
                            const active = isItemActive(item)
                            const Icon = item.icon
                            return (
                              <AppLink
                                key={item.id}
                                to={item.path ?? '#'}
                                onClick={() => onOpenChange(false)}
                                className={clsx(
                                  'flex items-center gap-3 rounded-xl border px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                                  active
                                    ? 'border-primary/70 bg-primary/10 text-primary'
                                    : 'border-transparent bg-transparent hover:border-border/60 hover:bg-muted/10',
                                )}
                                aria-current={active ? 'page' : undefined}
                              >
                                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/20 text-muted-foreground">
                                  <Icon className="h-4 w-4" aria-hidden="true" />
                                </span>
                                <div className="flex flex-col">
                                  <span className="font-medium text-foreground">{item.label}</span>
                                  {item.description && (
                                    <span className="text-xs text-muted-foreground">{item.description}</span>
                                  )}
                                </div>
                                <ChevronRightIcon className="ml-auto h-4 w-4 text-muted-foreground" aria-hidden="true" />
                              </AppLink>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </nav>

                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Быстрые действия AI</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {COMMAND_ACTIONS.map(action => (
                        <AppLink
                          key={action.id}
                          to={action.path ?? '#'}
                          onClick={() => onOpenChange(false)}
                          className="flex items-center gap-2 rounded-xl border border-dashed border-primary/50 bg-primary/5 px-2 py-2 text-xs font-semibold text-primary transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                          <SparklesIcon className="h-4 w-4" aria-hidden="true" />
                          {action.label}
                        </AppLink>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-t border-border/60 px-4 py-4 text-xs text-muted-foreground">
                  <div className="flex items-center justify-between">
                    <span>CaloIQ 3.8 · Legend</span>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex items-center gap-1 rounded-lg px-2 py-1 transition hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive"
                    >
                      <ExternalLinkIcon className="h-3.5 w-3.5" aria-hidden="true" />
                      Выйти
                    </button>
                  </div>
                </div>
              </motion.aside>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export default NavDrawer