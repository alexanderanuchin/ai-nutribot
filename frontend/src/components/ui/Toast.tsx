import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import * as RadixToast from '@radix-ui/react-toast'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { CheckCircle2Icon, InfoIcon, ShieldAlertIcon, XIcon } from 'lucide-react'
import clsx from 'clsx'

type ToastTone = 'default' | 'success' | 'warning' | 'destructive'

export interface ToastMessage {
  id: string
  title: string
  description?: string
  tone?: ToastTone
  duration?: number
}

interface ToastContextValue {
  notify: (message: Omit<ToastMessage, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

const toneStyles: Record<ToastTone, string> = {
  default: 'bg-card/95 text-foreground border-border/70',
  success: 'bg-success/15 text-success border-success/40',
  warning: 'bg-warning/15 text-warning border-warning/45',
  destructive: 'bg-destructive/15 text-destructive border-destructive/40',
}

const toneIcons: Record<ToastTone, ReactNode> = {
  default: <InfoIcon className="h-4 w-4" aria-hidden="true" />,
  success: <CheckCircle2Icon className="h-4 w-4" aria-hidden="true" />,
  warning: <ShieldAlertIcon className="h-4 w-4" aria-hidden="true" />,
  destructive: <ShieldAlertIcon className="h-4 w-4" aria-hidden="true" />,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([])
  const shouldReduceMotion = useReducedMotion()

  const notify = useCallback((message: Omit<ToastMessage, 'id'>) => {
    setMessages(previous => [
      ...previous,
      {
        id: crypto.randomUUID(),
        tone: 'default',
        duration: 4000,
        ...message,
      },
    ])
  }, [])

  const remove = useCallback((id: string) => {
    setMessages(previous => previous.filter(item => item.id !== id))
  }, [])

  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider duration={4000} swipeDirection="right">
        {children}
        <RadixToast.Viewport className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex flex-col gap-3 md:inset-x-auto md:bottom-8 md:right-8 md:w-96" />
        <AnimatePresence>
          {messages.map(message => {
            const tone = message.tone ?? 'default'
            return (
              <RadixToast.Root asChild key={message.id} onOpenChange={open => !open && remove(message.id)} duration={message.duration}>
                <motion.div
                  className={clsx(
                    'pointer-events-auto flex w-full items-start gap-3 rounded-2xl border px-4 py-3 shadow-level-2 backdrop-blur-lg',
                    toneStyles[tone],
                  )}
                  initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
                  animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, transition: { type: 'spring', damping: 26, stiffness: 220 } }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12, transition: { duration: 0.18 } }}
                >
                  <span className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-muted/20">
                    {toneIcons[tone]}
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <RadixToast.Title className="text-sm font-semibold text-foreground">{message.title}</RadixToast.Title>
                    {message.description ? (
                      <RadixToast.Description className="text-sm text-muted-foreground">
                        {message.description}
                      </RadixToast.Description>
                    ) : null}
                  </div>
                  <RadixToast.Close asChild>
                    <button
                      type="button"
                      className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full bg-transparent text-foreground transition hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label="Закрыть уведомление"
                    >
                      <XIcon className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </RadixToast.Close>
                </motion.div>
              </RadixToast.Root>
            )
          })}
        </AnimatePresence>
      </RadixToast.Provider>
    </ToastContext.Provider>
  )
}

export default ToastProvider