import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { XIcon } from 'lucide-react'
import { useId } from 'react'

import Button from './Button'
import IconButton from './IconButton'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'default' | 'destructive'
  loading?: boolean
  onConfirm: () => void
  onOpenChange: (open: boolean) => void
}

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}

const contentVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1 },
}

export function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  tone = 'default',
  loading = false,
}: ConfirmDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-[100] bg-background/80 backdrop-blur-sm"
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={overlayVariants}
                transition={{ duration: 0.18 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <motion.div
                role="alertdialog"
                aria-modal="true"
                aria-labelledby={titleId}
                aria-describedby={description ? descriptionId : undefined}
                className="fixed left-1/2 top-1/2 z-[101] w-[min(420px,90vw)] -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-border/60 bg-card/95 p-6 shadow-level-3"
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={contentVariants}
                transition={{ duration: 0.2 }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <Dialog.Title id={titleId} className="text-base font-semibold text-foreground">
                      {title}
                    </Dialog.Title>
                    {description ? (
                      <Dialog.Description id={descriptionId} className="mt-2 text-sm text-muted-foreground">
                        {description}
                      </Dialog.Description>
                    ) : null}
                  </div>
                  <Dialog.Close asChild>
                    <IconButton
                      variant="ghost"
                      size="sm"
                      aria-label="Закрыть диалог подтверждения"
                      disabled={loading}
                    >
                      <XIcon className="h-4 w-4" aria-hidden="true" />
                    </IconButton>
                  </Dialog.Close>
                </div>
                <div className="mt-6 flex justify-end gap-3">
                  <Dialog.Close asChild>
                    <Button type="button" variant="ghost" size="sm" disabled={loading}>
                      {cancelLabel}
                    </Button>
                  </Dialog.Close>
                  <Button
                    type="button"
                    variant={tone === 'destructive' ? 'destructive' : 'primary'}
                    size="sm"
                    onClick={onConfirm}
                    loading={loading}
                  >
                    {confirmLabel}
                  </Button>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export default ConfirmDialog
