import { type ReactNode } from 'react'
import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import clsx from 'clsx'

interface SegmentedControlOption {
  value: string
  label: ReactNode
}

interface SegmentedControlProps {
  value: string
  onValueChange: (value: string) => void
  options: SegmentedControlOption[]
  className?: string
}

export function SegmentedControl({ value, onValueChange, options, className }: SegmentedControlProps) {
  return (
    <ToggleGroupPrimitive.Root
      type="single"
      value={value}
      onValueChange={onValueChange}
      className={clsx('inline-flex items-center gap-1 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-level-1', className)}
      aria-label="Переключатель сортировки"
    >
      {options.map(option => (
        <ToggleGroupPrimitive.Item
          key={option.value}
          value={option.value}
          className="flex min-h-[2.75rem] min-w-[3.25rem] items-center justify-center rounded-xl px-3 py-1.5 text-sm font-semibold text-muted-foreground transition data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-level-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {option.label}
        </ToggleGroupPrimitive.Item>
      ))}
    </ToggleGroupPrimitive.Root>
  )
}

export default SegmentedControl