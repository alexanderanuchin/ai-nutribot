import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { BadgeCheckIcon, CopyIcon, InfoIcon, Link2Icon, QrCodeIcon, RefreshCwIcon, ShieldAlertIcon } from 'lucide-react'

import Button from '../ui/Button'
import { useToast } from '../ui'
import { TelegramStatusResponse } from '../../api/telegram'
import { generateQrDataUrl } from '../../lib/qr'

interface TelegramStatusCardProps {
  status?: TelegramStatusResponse
  onCreateLink: () => void
  loading?: boolean
}

export function TelegramStatusCard({ status, onCreateLink, loading }: TelegramStatusCardProps) {
  const [qr, setQr] = useState<string>('')
  const { notify } = useToast()

  useEffect(() => {
    if (!status?.link?.links?.tme) return
    generateQrDataUrl(status.link.links.tme).then(setQr).catch(() => setQr(''))
  }, [status?.link?.links?.tme])

  const linkedLabel = status?.linked ? 'Связано' : 'Не связано'
  const identifier = status?.telegram_id ? `ID ${status.telegram_id}` : 'Ожидаем авторизацию через Mini App'

  const telegramUsername = status?.telegram_username || '—'
  const appUsername = status?.app_username || '—'

  const copyLink = async () => {
    if (!status?.link?.links?.tme) return
    try {
      await navigator.clipboard.writeText(status.link.links.tme)
      notify({ title: 'Ссылка скопирована', tone: 'success' })
    } catch (error) {
      notify({
        title: 'Не удалось скопировать',
        description: error instanceof Error ? error.message : undefined,
        tone: 'warning',
      })
    }
  }

  return (
    <motion.div
      className="rounded-2xl border border-border/60 bg-card p-4 shadow-level-1"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-semibold">
            {status?.linked ? (
              <BadgeCheckIcon className="h-4 w-4 text-green-500" />
            ) : (
              <ShieldAlertIcon className="h-4 w-4 text-amber-500" />
            )}
            <span>{linkedLabel}</span>
          </div>
          <div className="text-sm text-muted-foreground">{identifier}</div>
          {status?.link?.code && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <InfoIcon className="h-3.5 w-3.5" /> payload: {status.link.code}
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onCreateLink}
            disabled={loading}
            aria-label="Обновить deep-link"
          >
            <RefreshCwIcon className="mr-2 h-4 w-4" /> Обновить deep‑link
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={copyLink}
            disabled={!status?.link?.links?.tme}
            aria-label="Скопировать ссылку"
          >
            <CopyIcon className="mr-2 h-4 w-4" /> Скопировать ссылку
          </Button>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-dashed border-border/60 p-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Link2Icon className="h-4 w-4" /> Deep‑links
          </div>
          <div className="mt-2 space-y-1">
            <div className="font-mono text-xs text-foreground">{status?.link?.links?.tme}</div>
            <div className="font-mono text-xs text-foreground">{status?.link?.links?.startapp}</div>
          </div>
        </div>
        <div className="rounded-xl border border-dashed border-border/60 p-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <QrCodeIcon className="h-4 w-4" /> QR
          </div>
          <div className="mt-2 flex items-center gap-3">
            {qr ? (
              <img src={qr} alt="QR" className="h-20 w-20 rounded-lg border border-border/70" />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-lg border border-border/70 text-muted-foreground">
                <QrCodeIcon className="h-5 w-5" />
              </div>
            )}
            <div className="text-xs text-muted-foreground">Используйте для быстрого старта Mini App с параметром.</div>
          </div>
        </div>
        <div className="rounded-xl border border-dashed border-border/60 p-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <InfoIcon className="h-4 w-4" /> Диагностика
          </div>
          <div className="mt-2 space-y-1 text-xs">
            <div>Связано: {String(status?.linked ?? false)}</div>
            <div>Обновлено: {status?.linked_at ? new Date(status.linked_at).toLocaleString() : '—'}</div>
            <div>Срок ссылки: {status?.link?.expires_at ? new Date(status.link.expires_at).toLocaleString() : '—'}</div>
            <div>Аккаунт (приложение): {appUsername}</div>
            <div>Telegram username: {telegramUsername}</div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
