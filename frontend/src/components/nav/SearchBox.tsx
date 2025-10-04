import type { ChangeEvent } from 'react'
import { SearchIcon } from 'lucide-react'
import clsx from 'clsx'

export interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
  className?: string
}

export function SearchBox({ value, onChange, placeholder = 'Поиск', autoFocus, className }: SearchBoxProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value)
  }

  return (
    <label className={clsx('relative flex items-center gap-2 rounded-2xl border border-border/60 bg-background/90 px-3 py-2 text-sm shadow-soft focus-within:ring-2 focus-within:ring-primary', className)}>
      <SearchIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">{placeholder}</span>
      <input
        type="search"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className="flex-1 border-none bg-transparent text-base text-foreground placeholder:text-muted focus:outline-none"
        autoFocus={autoFocus}
        aria-label={placeholder}
      />
      <kbd className="hidden rounded-md border border-border/80 bg-muted/20 px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground sm:block">
        ⌘K
      </kbd>
    </label>
  )
}

export default SearchBox