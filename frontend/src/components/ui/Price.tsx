interface PriceProps {
  value: number
  currency?: string
  originalValue?: number | null
  className?: string
}

export function Price({ value, currency = 'RUB', originalValue, className }: PriceProps) {
  const formatter = new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  })
  const formatted = formatter.format(value)
  const original = originalValue ? formatter.format(originalValue) : null

  return (
    <div className={className}>
      <span className="text-lg font-semibold text-foreground">{formatted}</span>
      {original && originalValue && originalValue > value ? (
        <span className="ml-2 text-sm text-muted-foreground line-through">{original}</span>
      ) : null}
    </div>
  )
}

export default Price