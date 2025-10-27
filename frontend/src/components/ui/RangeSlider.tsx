import * as SliderPrimitive from '@radix-ui/react-slider'
import clsx from 'clsx'

interface RangeSliderProps extends Omit<SliderPrimitive.SliderProps, 'onValueChange' | 'value' | 'defaultValue'> {
  value: [number, number]
  onValueChange: (value: [number, number]) => void
  min?: number
  max?: number
  step?: number
  className?: string
}

export function RangeSlider({ value, onValueChange, min = 0, max = 100, step = 1, className, ...props }: RangeSliderProps) {
  return (
    <SliderPrimitive.Root
      value={value}
      onValueChange={newValue => onValueChange([newValue[0], newValue[1]])}
      min={min}
      max={max}
      step={step}
      className={clsx('relative flex w-full touch-none select-none items-center', className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-2 w-full overflow-hidden rounded-full bg-muted/20">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        className="block h-6 w-6 rounded-full border border-border bg-card shadow-level-2 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Минимальное значение"
      />
      <SliderPrimitive.Thumb
        className="block h-6 w-6 rounded-full border border-border bg-card shadow-level-2 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Максимальное значение"
      />
    </SliderPrimitive.Root>
  )
}

export default RangeSlider