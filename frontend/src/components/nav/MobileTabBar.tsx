import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import * as Dialog from '@radix-ui/react-dialog'
import Lottie from 'lottie-react'
import Ai_bot from '../../assets/Ai_bot.json'
import clsx from 'clsx'
import { PRIMARY_NAVIGATION, COMMAND_ACTIONS } from '../../navigation/schema'
import { useActiveRoute } from '../../hooks/useActiveRoute'
import { useSafeArea } from '../../hooks/useSafeArea'
import { AppLink } from './AppLink'

export interface MobileTabBarProps {
  onOpenCommand: () => void
}

export function MobileTabBar({ onOpenCommand }: MobileTabBarProps) {
  const { isItemActive } = useActiveRoute()
  const safeArea = useSafeArea({ inset: 12, edges: ['bottom', 'left', 'right'] })
  const [fabOpen, setFabOpen] = useState(false)

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border/60 bg-background/95 shadow-2xl backdrop-blur-xl lg:hidden"
      style={safeArea}
    >
      <div className="relative flex items-center justify-around gap-2">
        {PRIMARY_NAVIGATION.map(item => {
          const Icon = item.icon
          const active = isItemActive(item)
          return (
            <AppLink
              key={item.id}
              to={item.path ?? '#'}
              aria-current={active ? 'page' : undefined}
              className={clsx(
                'flex flex-1 flex-col items-center gap-1 rounded-2xl px-2 py-3 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                active ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span className={clsx('flex h-9 w-9 items-center justify-center rounded-full border', active ? 'border-primary/80 bg-primary/10' : 'border-transparent bg-muted/20')}>
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              {item.label}
            </AppLink>
          )
        })}
        <Dialog.Root open={fabOpen} onOpenChange={setFabOpen}>
          <Dialog.Trigger asChild>
            <motion.button
              type="button"
              className="absolute top-[-3.5rem] left-[1rem] inline-flex h-fit w-fit -translate-x-1/2 items-center justify-center rounded-full bg-transparent text-primary-foreground shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary p-0"
              aria-label="AI быстрые действия"
              whileTap={{ scale: 0.94 }}
              whileHover={{ scale: 1.05 }}
            >
              <Lottie
                animationData={Ai_bot}
                loop
                autoplay
                // размеры анимации управляют размерами кнопки
                style={{ width: 100, height: 100, pointerEvents: 'none' }}
                // корректное масштабирование без искажений
                rendererSettings={{ preserveAspectRatio: 'xMidYMid meet' }}
                aria-hidden
              />
            </motion.button>
          </Dialog.Trigger>
          <AnimatePresence>
            {fabOpen ? (
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
                    initial={{ y: '100%' }}
                    animate={{ y: 0 }}
                    exit={{ y: '100%' }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="fixed inset-x-4 bottom-4 z-50 rounded-3xl border border-border/80 bg-background/98 p-4 shadow-2xl backdrop-blur-xl"
                  >
                    <Dialog.Title className="sr-only">AI быстрые действия</Dialog.Title>
                    <Dialog.Description className="sr-only">Выберите одно из быстрых действий ассистента</Dialog.Description>
                    <div className="mb-3 flex items-center justify-between">
                      <div>
                        <h2 className="text-base font-semibold text-foreground">AI ассистент</h2>
                        <p className="text-xs text-muted-foreground">Сделайте шаг к идеальному плану</p>
                      </div>
                      <button
                        type="button"
                        className="text-xs font-semibold text-primary"
                        onClick={() => {
                          setFabOpen(false)
                          onOpenCommand()
                        }}
                      >
                        Команды
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {COMMAND_ACTIONS.map(action => (
                        <AppLink
                          key={action.id}
                          to={action.path ?? '#'}
                          className="flex flex-col gap-1 rounded-2xl border border-dashed border-primary/60 bg-primary/5 px-3 py-3 text-left text-xs font-semibold text-primary transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                          onClick={() => setFabOpen(false)}
                        >
                          {action.label}
                          <span className="text-[11px] font-normal text-muted-foreground">{action.description}</span>
                        </AppLink>
                      ))}
                    </div>
                  </motion.div>
                </Dialog.Content>
              </Dialog.Portal>
            ) : null}
          </AnimatePresence>
        </Dialog.Root>
      </div>
    </div>
  )
}

export default MobileTabBar