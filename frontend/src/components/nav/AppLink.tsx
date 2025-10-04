import { forwardRef } from 'react'
import type { AnchorHTMLAttributes, ForwardRefExoticComponent, ReactNode, RefAttributes } from 'react'
import { useHref, useLinkClickHandler } from 'react-router-dom'
import type { To } from 'react-router-dom'

export interface AppLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  to: To
  replace?: boolean
  state?: unknown
  prefetch?: boolean
  children?: ReactNode
}

export type AppLinkComponent = ForwardRefExoticComponent<AppLinkProps & RefAttributes<HTMLAnchorElement>>

const RouterLink = forwardRef<HTMLAnchorElement, AppLinkProps>(function RouterLink(
  { to, replace, state, target, onClick, children, ...rest },
  ref,
) {
  const href = useHref(to)
  const handleClick = useLinkClickHandler(to, {
    replace,
    state,
    target,
  })

  return (
    <a
      {...rest}
      ref={ref}
      href={href}
      onClick={event => {
        onClick?.(event)
        if (!event.defaultPrevented) {
          handleClick(event)
        }
      }}
    >
      {children}
    </a>
  )
})

let ActiveLinkComponent: AppLinkComponent = RouterLink

export function setAppLinkComponent(component: AppLinkComponent) {
  ActiveLinkComponent = component
}

export const AppLink = forwardRef<HTMLAnchorElement, AppLinkProps>((props, ref) => {
  return <ActiveLinkComponent {...props} ref={ref} />
})

AppLink.displayName = 'AppLink'