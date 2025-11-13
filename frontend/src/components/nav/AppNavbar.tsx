import { useEffect, useRef, useState } from 'react'
import { MenuIcon, BellIcon, WifiOffIcon } from 'lucide-react'
import clsx from 'clsx'
import Logo from '../Logo'
import { useActiveRoute } from '../../hooks/useActiveRoute'
import { PRIMARY_NAVIGATION, SECONDARY_NAVIGATION } from '../../navigation/schema'
import { useSafeArea } from '../../hooks/useSafeArea'
import ThemeToggle from './ThemeToggle'
import WalletBadge from './WalletBadge'
import BotBalanceBadge from './BotBalanceBadge'
import UserMenu from './UserMenu'
import { useTheme } from '../../hooks/useTheme'

export interface AppNavbarProps {
  onMenuClick: () => void
  onOpenCommand: () => void
  onLogout?: () => void
}

export function AppNavbar({ onMenuClick, onOpenCommand, onLogout }: AppNavbarProps) {
  const safeArea = useSafeArea({ inset: 14, edges: ['top', 'left', 'right'] })
  const [isOnline, setIsOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))
  const [isHidden, setIsHidden] = useState(false)
  const [isElevated, setIsElevated] = useState(false)
  const lastScrollYRef = useRef(0)
  const { findActiveTrail } = useActiveRoute()
  const trail = findActiveTrail(SECONDARY_NAVIGATION, PRIMARY_NAVIGATION)
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    let frame = 0

    const updateScrollState = () => {
      const current = window.scrollY
      const previous = lastScrollYRef.current
      const delta = current - previous

      if (current <= 0) {
        setIsHidden(false)
      } else if (delta > 6 && current > 72) {
        setIsHidden(true)
      } else if (delta < -6) {
        setIsHidden(false)
      }

      setIsElevated(current > 16)
      lastScrollYRef.current = current
    }

    const handleScroll = () => {
      if (frame) {
        cancelAnimationFrame(frame)
      }
      frame = window.requestAnimationFrame(updateScrollState)
    }

    updateScrollState()
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      if (frame) {
        cancelAnimationFrame(frame)
      }
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  const headerClassName = clsx(
    'sticky top-0 z-40 w-full border-b transition-all duration-300 ease-out will-change-transform',
    'backdrop-blur-xl',
    isElevated ? 'border-border/70 bg-background/95 shadow-level-2' : 'border-transparent bg-background/80 shadow-none',
    isHidden ? '-translate-y-full opacity-0 pointer-events-none' : 'translate-y-0 opacity-100',
    resolvedTheme === 'dark' ? 'text-slate-100' : 'text-slate-900',
  )

  return (
    <header className={headerClassName} style={safeArea}>
      <div className="mx-auto grid w-full max-w-6xl grid-cols-[auto_1fr] items-start gap-x-3 gap-y-2 px-3 py-3 sm:grid-cols-[auto_1fr_auto] sm:items-center">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border/60 bg-transparent text-slate-700 transition-colors duration-200 hover:border-border/80 hover:bg-slate-900/5 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/30 active:scale-95 dark:text-slate-100 dark:hover:bg-slate-100/10 dark:hover:text-slate-100 dark:focus-visible:ring-slate-100/30 lg:hidden"
            aria-label="Открыть меню"
          >
            <MenuIcon className="h-5 w-5" aria-hidden="true" />
          </button>
          <Logo className="h-7 w-auto" />
        </div>

        <div className="hidden min-w-0 flex-col text-xs text-muted-foreground sm:flex">
          <span className="truncate">CaloIQ Personal CRM</span>
          <span className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-sky-700 dark:text-sky-300">
            {trail.length > 0 ? trail.map(item => item.label).join(' › ') : 'Личный кабинет'}
          </span>
        </div>

        <div className="flex w-full min-w-0 flex-wrap items-center justify-end gap-1.5 sm:w-auto sm:flex-nowrap sm:justify-self-end sm:gap-2">
          {!isOnline && (
            <span className="flex items-center gap-1 rounded-full border border-dashed border-destructive/60 bg-destructive/10 px-2 py-1 text-xs font-semibold text-destructive">
              <WifiOffIcon className="h-4 w-4" aria-hidden="true" />
              offline
            </span>
          )}
          <BotBalanceBadge />
          <WalletBadge />
          <ThemeToggle />
          <button
            type="button"
            className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-border/60 bg-transparent text-slate-700 transition-colors duration-200 hover:border-border/80 hover:bg-slate-900/5 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/30 active:scale-95 dark:text-slate-100 dark:hover:bg-slate-100/10 dark:hover:text-slate-100 dark:focus-visible:ring-slate-100/30 sm:flex"
          >
            <BellIcon className="h-5 w-5" aria-hidden="true" />
          </button>
          <UserMenu onLogout={onLogout} onOpenCommand={onOpenCommand} />
        </div>
      </div>
    </header>
  )
}

export default AppNavbar
