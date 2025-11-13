import { useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import { CommandIcon, LogOutIcon, Settings2Icon, UserRoundIcon } from 'lucide-react'
import clsx from 'clsx'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { AppLink } from './AppLink'
import { getAvatarPreset } from '../../utils/avatar'

export interface UserMenuProps {
  onLogout?: () => void
  onOpenCommand?: () => void
}

export function UserMenu({ onLogout, onOpenCommand }: UserMenuProps) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  if (!user) return null

  const handleLogout = () => {
    logout()
    onLogout?.()
    setOpen(false)
    navigate('/login', { replace: true })
  }

  const initials = user.fullName
    .split(' ')
    .filter(Boolean)
    .map(part => part[0]?.toUpperCase())
    .slice(0, 2)
    .join('')
  const avatarPreset = user.avatarState.kind === 'preset' ? getAvatarPreset(user.avatarState.id) ?? null : null
  const avatarImageSrc = user.avatarImageSrc

  const handleCommandOpen = () => {
    if (!onOpenCommand) return
    onOpenCommand()
    setOpen(false)
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          // Убираем синий фон/hover, ставим пунктирную овальную рамку цветом иконки (currentColor = primary).
          className="relative flex min-w-0 items-center gap-2 rounded-full border border-dashed border-current bg-transparent px-1.5 py-1.5 text-left text-sm transition focus-visible:outline-none focus-visible:ring-0 sm:pl-2 sm:pr-3 text-muted/20"
        >
          <span
            className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-primary/15 text-sm font-semibold text-primary"
            style={avatarPreset ? { background: avatarPreset.gradient } : undefined}
          >
            {avatarImageSrc ? (
              <img
                src={avatarImageSrc}
                alt={user.fullName}
                className="h-full w-full rounded-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : user.avatarState.kind === 'preset' && avatarPreset ? (
              <span className="text-base" aria-hidden="true">
                {avatarPreset.emoji}
              </span>
            ) : initials ? (
              initials
            ) : (
              <UserRoundIcon className="h-4 w-4" aria-hidden="true" />
            )}
          </span>
          <span className="hidden min-w-0 flex-col leading-tight lg:flex">
            <span className="text-xs font-medium text-muted-foreground">{user.mode}</span>
            <span className="text-sm font-semibold text-foreground">{user.fullName}</span>
          </span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={12}
          className="z-50 w-64 rounded-2xl border border-border/70 bg-popover/95 p-3 shadow-2xl backdrop-blur-lg"
        >
          <div className="mb-3 flex flex-col gap-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{user.role}</span>
            <span className="text-base font-semibold text-foreground">{user.fullName}</span>
            <span className="text-xs text-muted-foreground">{user.email}</span>
          </div>
          <nav className="flex flex-col gap-1" aria-label="Настройки пользователя">
            {onOpenCommand && (
              <button
                type="button"
                onClick={handleCommandOpen}
                className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <CommandIcon className="h-4 w-4" aria-hidden="true" />
                Командная палитра
                <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/80">Cmd/Ctrl + K</span>
              </button>
            )}
            <AppLink
              to="/profile"
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition hover:bg-muted/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              onClick={() => setOpen(false)}
            >
              <UserRoundIcon className="h-4 w-4" aria-hidden="true" />
              Профиль
            </AppLink>
            <AppLink
              to="/settings"
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition hover:bg-muted/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              onClick={() => setOpen(false)}
            >
              <Settings2Icon className="h-4 w-4" aria-hidden="true" />
              Настройки
            </AppLink>
          </nav>
          <button
            type="button"
            onClick={handleLogout}
            className={clsx(
              'mt-3 flex w-full items-center gap-2 rounded-xl border border-transparent px-3 py-2 text-sm text-destructive transition',
              'hover:border-destructive/40 hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive',
            )}
          >
            <LogOutIcon className="h-4 w-4" aria-hidden="true" />
            Выйти
          </button>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}

export default UserMenu
