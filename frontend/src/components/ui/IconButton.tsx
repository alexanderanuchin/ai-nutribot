import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'surface' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  active?: boolean
}

const MotionButton = motion.button

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { className, variant = 'surface', size = 'md', active = false, ...props },
  ref,
) {
  const shouldReduceMotion = useReducedMotion()
  return (
    <MotionButton
      ref={ref}
      className={clsx(
        'inline-flex items-center justify-center rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60',
        size === 'sm' && 'h-10 w-10 text-sm',
        size === 'md' && 'h-11 w-11 text-base',
        size === 'lg' && 'h-12 w-12 text-lg',
        variant === 'primary' && 'bg-primary text-primary-foreground shadow-level-2 hover:bg-primary/90',
        variant === 'surface' && 'bg-card text-foreground shadow-level-1 hover:bg-muted/20',
        variant === 'ghost' && 'bg-transparent text-foreground hover:bg-muted/20',
        variant === 'destructive' && 'bg-destructive text-primary-foreground shadow-level-2 hover:bg-destructive/85',
        active && 'ring-2 ring-ring ring-offset-2 ring-offset-background',
        className,
      )}
      whileHover={shouldReduceMotion ? undefined : { y: -1, scale: 1.02 }}
      whileTap={shouldReduceMotion ? undefined : { scale: 0.96, y: 0 }}
      transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}
      {...props}
    />
  )
})

export default IconButton