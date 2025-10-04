import { useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import { MonitorCogIcon, MoonIcon, SunIcon } from 'lucide-react'
import clsx from 'clsx'
import { useTheme, type ThemeMode } from '../../hooks/useTheme'

const THEME_OPTIONS: Array<{ value: ThemeMode; label: string; description: string; icon: React.ComponentType<{ className?: string }> }> = [
  { value: 'light', label: 'Светлая', description: 'Яркий UI для дневного режима', icon: SunIcon },
  { value: 'dark', label: 'Тёмная', description: 'Контрастная UI для ночи', icon: MoonIcon },
  { value: 'system', label: 'Системная', description: 'Синхронизироваться с устройством', icon: MonitorCogIcon },
]

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const [open, setOpen] = useState(false)

  const ActiveIcon = resolvedTheme === 'dark' ? MoonIcon : SunIcon

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label="Переключатель темы"
          className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/80 text-foreground shadow-soft transition hover:shadow-ring-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <ActiveIcon className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Текущая тема: {resolvedTheme === 'dark' ? 'тёмная' : 'светлая'}</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={12}
          className="z-50 w-64 rounded-2xl border border-border/60 bg-popover/90 p-3 backdrop-blur-lg shadow-xl focus:outline-none"
        >
          <div className="space-y-2" role="radiogroup" aria-label="Выбор темы">
            {THEME_OPTIONS.map(option => {
              const Icon = option.icon
              const active = theme === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => {
                    setTheme(option.value)
                    setOpen(false)
                  }}
                  className={clsx(
                    'w-full rounded-xl border px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                    active
                      ? 'border-primary/80 bg-primary/10 text-primary'
                      : 'border-transparent bg-transparent hover:border-border/80 hover:bg-muted/10',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-1 rounded-full bg-primary/10 p-1 text-primary">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <div>
                      <div className="text-sm font-semibold leading-tight">{option.label}</div>
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}

export default ThemeToggle