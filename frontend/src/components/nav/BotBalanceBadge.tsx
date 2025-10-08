import clsx from 'clsx'
import { BotIcon } from 'lucide-react'
import { useAuthContext } from '../../providers/AuthProvider'
import useBotStarsBalance from '../../hooks/useBotStarsBalance'

export interface BotBalanceBadgeProps {
  className?: string
}

export function BotBalanceBadge({ className }: BotBalanceBadgeProps) {
  const { user } = useAuthContext()
  const isStaff = Boolean(user?.isStaff)
  const { data, isLoading, isError } = useBotStarsBalance(isStaff)

  if (!isStaff) {
    return null
  }

  const amount = data?.amount ?? 0
  const currency = data?.currency ?? 'XTR'
  const updatedLabel = data?.updatedAt
    ? new Date(data.updatedAt).toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

  let displayText: string
  if (isLoading) {
    displayText = '•••'
  } else if (isError) {
    displayText = 'нет данных'
  } else {
    displayText = `${amount.toLocaleString('ru-RU')} ${currency}`
  }

  return (
    <div
      className={clsx(
        'hidden shrink-0 items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary shadow-soft sm:flex',
        className,
      )}
      aria-label="Баланс бота в Stars"
    >
      <BotIcon className="h-4 w-4" aria-hidden="true" />
      <span>{displayText}</span>
      <span className="text-[11px] font-normal text-muted-foreground">{isLoading ? 'обновление…' : `обновлён ${updatedLabel}`}</span>
    </div>
  )
}

export default BotBalanceBadge