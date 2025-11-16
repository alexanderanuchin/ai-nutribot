import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowRightIcon, QrCodeIcon, SmartphoneIcon, SparklesIcon } from 'lucide-react'

import Button from '../ui/Button'
import { generateQrDataUrl } from '../../lib/qr'

interface TelegramHeroCardProps {
  startLink?: string
  startAppLink?: string
  onOpenMiniApp: () => void
  onOpenTelegram: () => void
  loading?: boolean
}

export function TelegramHeroCard({
  startLink,
  startAppLink,
  onOpenMiniApp,
  onOpenTelegram,
  loading,
}: TelegramHeroCardProps) {
  const [qrUrl, setQrUrl] = useState<string>('')

  useEffect(() => {
    if (!startLink) return
    generateQrDataUrl(startLink).then(setQrUrl).catch(() => setQrUrl(''))
  }, [startLink])

  return (
    <motion.div
      className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-sky-600/20 via-indigo-600/20 to-slate-900/40 p-6 ring-1 ring-white/10 shadow-2xl"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex flex-col gap-3 md:max-w-[60%]">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/80 backdrop-blur">
            <SparklesIcon className="h-4 w-4" />
            Telegram Mini App
          </div>
          <h1 className="text-2xl font-semibold text-white md:text-3xl">Подключите Telegram</h1>
          <p className="max-w-2xl text-sm text-white/80 md:text-base">
            Авторизуйтесь через Mini App и управляйте кошельком Stars, планами и уведомлениями. Если Mini App открыт не в
            Telegram — используйте универсальную ссылку или QR, чтобы перейти в чат и завершить рукопожатие.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={onOpenMiniApp}
              disabled={loading}
              variant="primary"
              size="lg"
              aria-label="Открыть мини-приложение Telegram"
            >
              <div className="flex items-center gap-2">
                <SmartphoneIcon className="h-4 w-4" />
                Открыть мини‑приложение
              </div>
            </Button>
            <Button
              onClick={onOpenTelegram}
              disabled={loading}
              variant="outline"
              size="lg"
              aria-label="Открыть бота в Telegram"
            >
              <div className="flex items-center gap-2">
                <ArrowRightIcon className="h-4 w-4" />
                Открыть в Telegram
              </div>
            </Button>
          </div>
          {startAppLink && (
            <div className="text-xs text-white/70">
              Прямая ссылка Mini App: <span className="font-mono text-white">{startAppLink}</span>
            </div>
          )}
        </div>
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-white/10 p-4 text-white shadow-inner backdrop-blur">
          <div className="text-sm text-white/80">Откройте камеру Telegram и наведите</div>
          <div className="rounded-xl bg-white p-2 shadow-lg">
            {qrUrl ? (
              <img src={qrUrl} alt="QR для запуска в Telegram" className="h-40 w-40" />
            ) : (
              <div className="flex h-40 w-40 items-center justify-center text-white/70">
                <QrCodeIcon className="h-10 w-10" />
              </div>
            )}
          </div>
          {startLink && (
            <div className="flex items-center gap-2 text-xs text-white/80">
              <QrCodeIcon className="h-4 w-4" /> {startLink}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
