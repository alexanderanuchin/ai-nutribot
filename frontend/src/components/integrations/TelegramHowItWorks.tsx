import { motion } from 'framer-motion'
import { FingerprintIcon, MessageSquareIcon, ShieldCheckIcon } from 'lucide-react'

const steps = [
  {
    title: 'Откройте Mini App из клавиши',
    description: 'Нажмите inline‑кнопку, Mini App получит initData с query_id и пользователем.',
    icon: FingerprintIcon,
  },
  {
    title: 'Backend подтверждает авторизацию',
    description: 'initData обменивается на JWT на сервере, токены сохраняются и закрепляются за вашим Telegram ID.',
    icon: ShieldCheckIcon,
  },
  {
    title: 'В браузере — статус и ссылки',
    description: 'Видите статус связки, deep‑links и QR. Можно запустить Mini App или чат‑оболочку.',
    icon: MessageSquareIcon,
  },
]

export function TelegramHowItWorks() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {steps.map((step, index) => (
        <motion.div
          key={step.title}
          className="rounded-2xl border border-border/60 bg-card/60 p-4 shadow-level-1"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05, duration: 0.25 }}
        >
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary/10 p-2 text-primary">
              <step.icon className="h-5 w-5" />
            </div>
            <div className="text-sm font-semibold">{step.title}</div>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
        </motion.div>
      ))}
    </div>
  )
}
