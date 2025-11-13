import { forwardRef, type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { XIcon } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'

export const SheetRoot = Dialog.Root
export const SheetTrigger = Dialog.Trigger
export const SheetClose = Dialog.Close

export interface SheetContentProps extends Dialog.DialogContentProps {
  title?: string
  description?: string
  footer?: ReactNode
  side?: 'bottom' | 'right'
}

const MotionContent = motion.create(Dialog.Content)

export const SheetContent = forwardRef<HTMLDivElement, SheetContentProps>(function SheetContent(
  { className, title, description, children, footer, side = 'bottom', ...props },
  ref,
) {
  const shouldReduceMotion = useReducedMotion()
  return (
    <Dialog.Portal>
      <AnimatePresence initial={false}>
        <Dialog.Overlay asChild forceMount>
          <motion.div
            key="sheet-overlay"
            className="fixed inset-0 z-40 bg-black/45 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.18 } }}
            exit={{ opacity: 0, transition: { duration: 0.12 } }}
          />
        </Dialog.Overlay>
        <MotionContent
          key="sheet-content"
          forceMount
          ref={ref}
          className={clsx(
            'fixed z-50 flex max-h-[92vh] w-full flex-col gap-4 rounded-t-3xl border border-border/60 bg-card/98 p-6 shadow-level-3 backdrop-blur-xl focus:outline-none md:w-[480px]',
            side === 'right' && 'right-4 top-4 h-[calc(100vh-2rem)] max-h-none rounded-3xl md:bottom-4',
            side === 'bottom' && 'bottom-0 left-0 md:left-1/2 md:top-auto md:max-w-[520px] md:-translate-x-1/2 md:rounded-3xl md:bottom-6',
            className,
          )}
          initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: side === 'bottom' ? 32 : 16 }}
          animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, transition: { type: 'spring', damping: 24, stiffness: 240 } }}
          exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: side === 'bottom' ? 24 : 12, transition: { duration: 0.18 } }}
          {...props}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 flex-col gap-1">
              {title ? <Dialog.Title className="text-headline font-semibold text-foreground">{title}</Dialog.Title> : null}
              {description ? <Dialog.Description className="text-sm text-muted-foreground">{description}</Dialog.Description> : null}
            </div>
            <SheetClose asChild>
              <button
                type="button"
                className="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted/20 text-foreground transition hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <XIcon className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Закрыть</span>
              </button>
            </SheetClose>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
            {children}
          </div>
          {footer ? <div className="flex flex-col gap-2 pt-2">{footer}</div> : null}
        </MotionContent>
      </AnimatePresence>
    </Dialog.Portal>
  )
})

export const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('flex flex-col gap-2 text-center sm:text-left', className)} {...props} />
)

export const SheetFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('flex flex-col gap-3', className)} {...props} />
)

export const SheetDescription = Dialog.Description
export const SheetTitle = Dialog.Title

export default {
  Root: SheetRoot,
  Trigger: SheetTrigger,
  Close: SheetClose,
  Content: SheetContent,
  Header: SheetHeader,
  Footer: SheetFooter,
  Title: SheetTitle,
  Description: SheetDescription,
}