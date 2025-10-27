import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import clsx from 'clsx'

export const ToggleGroupRoot = ToggleGroupPrimitive.Root
export const ToggleGroupItem = ({ className, ...props }: ToggleGroupPrimitive.ToggleGroupItemProps) => (
  <ToggleGroupPrimitive.Item
    className={clsx(
      'inline-flex min-h-[2.75rem] min-w-[2.75rem] items-center justify-center rounded-xl border border-border/70 bg-card px-3 py-2 text-sm font-semibold text-foreground shadow-level-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:shadow-level-2',
      className,
    )}
    {...props}
  />
)

export default {
  Root: ToggleGroupRoot,
  Item: ToggleGroupItem,
}