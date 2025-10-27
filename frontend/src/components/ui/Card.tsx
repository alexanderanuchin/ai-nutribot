import { forwardRef } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean
  elevation?: 1 | 2 | 3
}

const MotionDiv = motion.div

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, interactive = false, elevation = 1, children, ...props },
  ref,
) {
  const shouldReduceMotion = useReducedMotion()
  const shadow = elevation === 3 ? 'shadow-level-3' : elevation === 2 ? 'shadow-level-2' : 'shadow-level-1'
  return (
    <MotionDiv
      ref={ref}
      className={clsx(
        'group relative rounded-2xl border border-border/70 bg-card/95 p-5 backdrop-blur-[12px] transition',
        shadow,
        interactive && 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      whileHover={interactive && !shouldReduceMotion ? { y: -2, scale: 1.01 } : undefined}
      whileTap={interactive && !shouldReduceMotion ? { scale: 0.995, y: 0 } : undefined}
      transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
      {...props}
    >
      {children}
    </MotionDiv>
  )
})

export default Card