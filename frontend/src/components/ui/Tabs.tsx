import * as TabsPrimitive from '@radix-ui/react-tabs'
import clsx from 'clsx'
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react'

type TabsListElement = ElementRef<typeof TabsPrimitive.List>
type TabsListProps = ComponentPropsWithoutRef<typeof TabsPrimitive.List>

type TabsTriggerElement = ElementRef<typeof TabsPrimitive.Trigger>
type TabsTriggerProps = ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>

type TabsContentElement = ElementRef<typeof TabsPrimitive.Content>
type TabsContentProps = ComponentPropsWithoutRef<typeof TabsPrimitive.Content>

export const TabsRoot = TabsPrimitive.Root

export const TabsList = forwardRef<TabsListElement, TabsListProps>(function TabsList(
  { className, ...props },
  ref,
) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={clsx(
        'inline-flex w-full items-center justify-start gap-2 rounded-2xl border border-border/60 bg-muted/20 p-1',
        className,
      )}
      {...props}
    />
  )
})

export const TabsTrigger = forwardRef<TabsTriggerElement, TabsTriggerProps>(function TabsTrigger(
  { className, children, ...props },
  ref,
) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={clsx(
        'group relative inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-3 py-2 text-sm font-semibold text-muted-foreground transition data-[state=active]:text-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
        className,
      )}
      {...props}
    >
      <span className="relative z-[1] flex items-center gap-2">{children}</span>
      <span
        aria-hidden="true"
        className="absolute inset-0 rounded-2xl bg-card opacity-0 shadow-level-1 transition group-data-[state=active]:opacity-100"
      />
    </TabsPrimitive.Trigger>
  )
})

export const TabsContent = forwardRef<TabsContentElement, TabsContentProps>(function TabsContent(
  { className, ...props },
  ref,
) {
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={clsx(
        'rounded-3xl border border-border/60 bg-background/70 p-4 shadow-level-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
        className,
      )}
      {...props}
    />
  )
})

export const Tabs = TabsRoot
