import { forwardRef, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactNode, type Ref } from 'react'
import { Loader2Icon } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'outline'
  | 'ghost'
  | 'success'
  | 'destructive'

export type ButtonSize = 'sm' | 'md' | 'lg'

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground shadow-level-2 hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring',
  secondary:
    'bg-muted/20 text-foreground shadow-level-1 hover:bg-muted/30 focus-visible:ring-2 focus-visible:ring-ring',
  outline:
    'border border-border bg-background text-foreground shadow-none hover:bg-muted/20 focus-visible:ring-2 focus-visible:ring-ring',
  ghost:
    'bg-transparent text-foreground hover:bg-muted/20 focus-visible:ring-2 focus-visible:ring-ring',
  success:
    'bg-success text-foreground shadow-level-2 hover:bg-success/90 focus-visible:ring-2 focus-visible:ring-ring',
  destructive:
    'bg-destructive text-primary-foreground shadow-level-2 hover:bg-destructive/90 focus-visible:ring-2 focus-visible:ring-ring',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-2 text-sm min-h-[2.75rem] min-w-[2.75rem] rounded-lg',
  md: 'px-4 py-2.5 text-sm md:text-base min-h-[3rem] min-w-[3rem] rounded-xl',
  lg: 'px-6 py-3 text-base min-h-[3.25rem] min-w-[3.25rem] rounded-2xl',
}

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leadingIcon?: ReactNode
  trailingIcon?: ReactNode
}

const MotionButton = motion.button
const MotionAnchor = motion.a

export const Button = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(function Button(
  {
    className,
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    leadingIcon,
    trailingIcon,
    disabled,
    href,
    target,
    rel,
    ...props
  },
  ref,
) {
  const shouldReduceMotion = useReducedMotion()
  const commonProps = {
    className: clsx(
      'relative inline-flex items-center justify-center gap-2 font-semibold transition focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60',
      variantClasses[variant],
      sizeClasses[size],
      className,
    ),
    whileHover: shouldReduceMotion ? undefined : { y: -2, scale: 1.01 },
    whileTap: shouldReduceMotion ? undefined : { scale: 0.985, y: 0 },
    transition: { duration: 0.22, ease: [0.2, 0.8, 0.2, 1] },
    children: (
      <>
        {loading ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" /> : leadingIcon ?? null}
        <span className="truncate">{children}</span>
        {trailingIcon ?? (loading ? <span className="sr-only">Загрузка</span> : null)}
      </>
    ),
  }
  if (href) {
    return (
      <MotionAnchor
        ref={ref as Ref<HTMLAnchorElement>}
        href={href}
        target={target}
        rel={rel}
        aria-disabled={disabled || loading}
        onClick={event => {
          if (disabled || loading) {
            event.preventDefault()
            event.stopPropagation()
          }
        }}
        {...commonProps}
        {...(props as AnchorHTMLAttributes<HTMLAnchorElement>)}
      />
    )
  }
  return (
    <MotionButton
      ref={ref as Ref<HTMLButtonElement>}
      disabled={disabled || loading}
      {...commonProps}
      {...props}
    />
  )
})

export default Button
