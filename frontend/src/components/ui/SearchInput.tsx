import { forwardRef, useEffect, type InputHTMLAttributes } from 'react'
import { CommandIcon, Loader2Icon, SearchIcon, XIcon } from 'lucide-react'
import clsx from 'clsx'

export interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  loading?: boolean
  onClear?: () => void
  shortcut?: string
  onShortcut?: () => void
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  { className, loading = false, onClear, shortcut = '⌘K', onShortcut, ...props },
  ref,
) {
  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'
      if (isShortcut) {
        event.preventDefault()
        onShortcut?.()
      }
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [onShortcut])

  return (
    <div
      className={clsx(
        'group relative flex w-full items-center gap-2 rounded-full border border-border/70 bg-card/95 px-4 py-2.5 shadow-level-1 transition focus-within:border-primary focus-within:shadow-level-2',
        'lg:rounded-[30px] lg:border-border/40 lg:bg-card/70 lg:px-6 lg:py-3 lg:shadow-[0_24px_72px_-48px_rgba(15,23,42,0.55)] lg:backdrop-blur',
        'lg:before:pointer-events-none lg:before:absolute lg:before:inset-0 lg:before:-z-10 lg:before:rounded-[30px] lg:before:bg-[radial-gradient(circle_at_left,color-mix(in_srgb,var(--primary)_32%,transparent)_0%,transparent_60%)] lg:before:opacity-0 lg:before:transition-opacity lg:hover:before:opacity-60 lg:focus-within:before:opacity-80',
        className,
      )}
    >
      <SearchIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      <input
        ref={ref}
        type="search"
        className="h-8 w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
        {...props}
      />
      {loading ? <Loader2Icon className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" /> : null}
      {props.value && (props.value as string).length > 0 && onClear ? (
        <button
          type="button"
          onClick={onClear}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Очистить поиск"
        >
          <XIcon className="h-4 w-4" aria-hidden="true" />
        </button>
      ) : null}
      <span className="hidden items-center gap-1 rounded-full border border-border/60 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground transition group-focus-within:bg-primary/10 group-focus-within:text-primary sm:flex">
        <CommandIcon className="h-3 w-3" aria-hidden="true" />
        {shortcut}
      </span>
    </div>
  )
})

export default SearchInput