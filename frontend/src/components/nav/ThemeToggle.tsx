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
          className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-border/60 bg-transparent text-slate-700 transition-colors duration-200 hover:border-border/70 hover:bg-slate-900/5 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/30 active:scale-95 dark:text-slate-100 dark:hover:bg-slate-100/10 dark:hover:text-slate-100 dark:focus-visible:ring-slate-100/30"
        >
          <ActiveIcon className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Текущая тема: {resolvedTheme === 'dark' ? 'тёмная' : 'светлая'}</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={12}
          className="z-50 w-64 rounded-2xl border border-border/60 bg-surface/95 p-3 text-slate-800 shadow-level-2 backdrop-blur-lg focus:outline-none dark:bg-surface/90 dark:text-slate-100"
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
                    'w-full rounded-xl border px-3 py-2 text-left text-slate-700 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/25 dark:text-slate-100 dark:focus-visible:ring-slate-100/25',
                    active
                      ? 'border-slate-900/70 bg-slate-900/5 text-slate-900 dark:border-slate-100/60 dark:bg-slate-100/10 dark:text-slate-100'
                      : 'border-transparent bg-transparent hover:border-border/70 hover:bg-slate-900/5 hover:text-slate-900 dark:hover:bg-slate-100/10 dark:hover:text-slate-100',
                  )}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={clsx(
                        'mt-1 rounded-full p-1 transition-colors',
                        active
                          ? 'bg-slate-900/10 text-slate-900 dark:bg-slate-100/15 dark:text-slate-100'
                          : 'bg-slate-900/5 text-slate-600 dark:bg-slate-100/10 dark:text-slate-300',
                      )}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <div>
                      <div className="text-sm font-semibold leading-tight">{option.label}</div>
                      <div className="text-xs text-muted-foreground dark:text-slate-400">{option.description}</div>
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
