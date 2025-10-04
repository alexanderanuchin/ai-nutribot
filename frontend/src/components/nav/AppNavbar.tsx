import { useEffect, useState } from 'react'
import { CommandIcon, MenuIcon, BellIcon, WifiOffIcon } from 'lucide-react'
import Logo from '../Logo'
import { useActiveRoute } from '../../hooks/useActiveRoute'
import { PRIMARY_NAVIGATION, SECONDARY_NAVIGATION } from '../../navigation/schema'
import { useSafeArea } from '../../hooks/useSafeArea'
import ThemeToggle from './ThemeToggle'
import WalletBadge from './WalletBadge'
import UserMenu from './UserMenu'

export interface AppNavbarProps {
  onMenuClick: () => void
  onOpenCommand: () => void
  onLogout?: () => void
}

export function AppNavbar({ onMenuClick, onOpenCommand, onLogout }: AppNavbarProps) {
  const safeArea = useSafeArea({ inset: 14, edges: ['top', 'left', 'right'] })
  const [isOnline, setIsOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))
  const { findActiveTrail } = useActiveRoute()
  const trail = findActiveTrail(SECONDARY_NAVIGATION, PRIMARY_NAVIGATION)

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

  return (
    <header
      className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl"
      style={safeArea}
    >
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-3 py-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/70 text-foreground transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary lg:hidden"
            aria-label="Открыть меню"
          >
            <MenuIcon className="h-5 w-5" aria-hidden="true" />
          </button>
          <Logo className="h-7 w-auto" />
          <div className="hidden flex-col text-xs text-muted-foreground sm:flex">
            <span>CaloIQ Personal CRM</span>
            <span className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-primary">
              {trail.length > 0 ? trail.map(item => item.label).join(' › ') : 'Личный кабинет'}
            </span>
          </div>
        </div>

        <div className="flex flex-1 items-center justify-end gap-2">
          <button
            type="button"
            onClick={onOpenCommand}
            className="hidden items-center gap-2 rounded-full border border-border/60 bg-background/80 px-3 py-2 text-sm font-semibold text-foreground shadow-soft transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:flex"
            aria-label="Командная палитра"
          >
            <CommandIcon className="h-4 w-4" aria-hidden="true" />
            Cmd / Ctrl + K
          </button>
          {!isOnline && (
            <span className="flex items-center gap-1 rounded-full border border-dashed border-destructive/60 bg-destructive/10 px-2 py-1 text-xs font-semibold text-destructive">
              <WifiOffIcon className="h-4 w-4" aria-hidden="true" />
              offline
            </span>
          )}
          <WalletBadge />
          <ThemeToggle />
          <button
            type="button"
            className="hidden h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/70 text-foreground transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:flex"
            aria-label="Уведомления"
          >
            <BellIcon className="h-5 w-5" aria-hidden="true" />
          </button>
          <UserMenu onLogout={onLogout} />
        </div>
      </div>
    </header>
  )
}

export default AppNavbar