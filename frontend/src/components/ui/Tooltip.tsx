import { useId, type ReactNode } from 'react'
import * as RadixTooltip from '@radix-ui/react-tooltip'
import { motion, useReducedMotion } from 'framer-motion'

export interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: RadixTooltip.TooltipContentProps['side']
  align?: RadixTooltip.TooltipContentProps['align']
  delayDuration?: number
}

export function Tooltip({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 120,
}: TooltipProps) {
  const shouldReduceMotion = useReducedMotion()
  const id = useId()

  return (
    <RadixTooltip.Provider delayDuration={delayDuration} skipDelayDuration={0} disableHoverableContent>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content asChild side={side} align={align} sideOffset={10} className="z-50">
            <motion.div
              role="tooltip"
              id={id}
              initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 4 }}
              animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, transition: { duration: 0.18 } }}
              exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 4, transition: { duration: 0.12 } }}
              className="max-w-xs rounded-xl border border-border/70 bg-card/95 px-3 py-2 text-xs font-medium text-foreground shadow-level-2 backdrop-blur"
            >
              {content}
              <RadixTooltip.Arrow className="fill-border/70" />
            </motion.div>
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  )
}

export default Tooltip