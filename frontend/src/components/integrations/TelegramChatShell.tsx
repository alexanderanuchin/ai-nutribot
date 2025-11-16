import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircleIcon, BotIcon, Loader2Icon, SendIcon, UserIcon } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'

import Button from '../ui/Button'
import { useToast } from '../ui'
import { sendBridgeMessage } from '../../api/telegram'
import api from '../../api/client'
import { tokenStore } from '../../utils/storage'

type ChatMessage = {
  id: string
  role: 'user' | 'bot' | 'system'
  text: string
  ts: string
}

interface TelegramChatShellProps {
  startAppLink?: string
}

export function TelegramChatShell({ startAppLink }: TelegramChatShellProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: 'system-intro',
    role: 'system',
    text: 'Это предпросмотр сообщений из нашего сервера. Полный чат и история остаются в Telegram, встроенного Telegram-чата на сайтах нет, поэтому используем собственную оболочку через серверный мост.',
    ts: new Date().toISOString(),
  }])
  const { notify } = useToast()
  const seenIds = useRef(new Set<string>(['system-intro']))
  const streamRef = useRef<EventSource | null>(null)
  const reconnectRef = useRef<number | null>(null)
  const scrollerRef = useRef<HTMLDivElement | null>(null)

  const baseApi = useMemo(() => {
    const base = api.defaults.baseURL || '/api'
    return base.endsWith('/') ? base.slice(0, -1) : base
  }, [])

  const sendMutation = useMutation({
    mutationFn: ({ text, clientId }: { text: string; clientId: string }) => sendBridgeMessage(text, clientId).then(() => clientId),
    onError: error => {
      notify({
        title: 'Не удалось отправить сообщение',
        description: error instanceof Error ? error.message : undefined,
        tone: 'warning',
      })
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'system',
          text: 'Не удалось отправить сообщение в бот. Попробуйте открыть Mini App по ссылке или QR.',
          ts: new Date().toISOString(),
        },
      ])
    },
  })

  const scrollToBottom = useCallback(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTo({ top: scrollerRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [])

  const startStream = useCallback(() => {
    const token = tokenStore.access
    const url = `${baseApi}/users/telegram/bridge/stream/${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const source = new EventSource(url)
    streamRef.current = source

    source.onmessage = event => {
      try {
        const data = JSON.parse(event.data)
        if (!data?.id || seenIds.current.has(data.id)) return
        seenIds.current.add(data.id)
        const role = data.type === 'bot_message' ? 'bot' : data.type === 'status' ? 'system' : 'user'
        setMessages(prev => [...prev, { id: data.id, role, text: data.text ?? '', ts: data.ts ?? new Date().toISOString() }])
      } catch {}
    }

    source.onerror = () => {
      source.close()
      notify({
        title: 'Поток событий остановлен',
        description: 'Переподключаемся… если проблема повторится, откройте Mini App в Telegram.',
        tone: 'warning',
      })
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current)
      }
      reconnectRef.current = window.setTimeout(() => startStream(), 2000)
    }
  }, [baseApi, notify])

  useEffect(() => {
    startStream()
    return () => {
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current)
      }
      streamRef.current?.close()
      streamRef.current = null
    }
  }, [startStream])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSend = (event?: FormEvent) => {
    event?.preventDefault()
    const text = input.trim()
    if (!text) return
    const clientId = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `local-${Date.now()}`
    setMessages(prev => [
      ...prev,
      { id: clientId, role: 'user', text, ts: new Date().toISOString() },
    ])
    seenIds.current.add(clientId)
    setInput('')
    sendMutation.mutate({ text, clientId })
  }

  return (
    <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-level-1">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <BotIcon className="h-4 w-4" /> Чат‑оболочка (бета)
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Только события, которые наш сервер обрабатывает. Полная переписка доступна в Telegram. Мини‑приложение лучше открывать из клавиши бота — встроенного Telegram-чата для сайтов не существует.
      </p>
      <div className="mt-3 flex flex-col gap-3">
        <div
          ref={el => {
            scrollerRef.current = el
          }}
          className="max-h-72 overflow-y-auto rounded-xl border border-border/60 bg-background/60 p-3"
        >
          {messages.map(message => (
            <motion.div
              key={message.id}
              className={`mb-2 flex items-start gap-2 ${message.role === 'user' ? 'justify-end text-right' : 'justify-start text-left'}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {message.role !== 'user' && (
                <div className="mt-1 rounded-full bg-muted p-1 text-muted-foreground">
                  {message.role === 'bot' ? <BotIcon className="h-4 w-4" /> : <AlertCircleIcon className="h-4 w-4" />}
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : message.role === 'bot'
                      ? 'bg-muted'
                      : 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-100'
                }`}
              >
                <div>{message.text}</div>
                <div className="mt-1 text-[10px] opacity-70">{new Date(message.ts).toLocaleTimeString()}</div>
              </div>
              {message.role === 'user' && (
                <div className="mt-1 rounded-full bg-primary/20 p-1 text-primary">
                  <UserIcon className="h-4 w-4" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
        <form className="flex items-center gap-2" onSubmit={handleSend}>
          <input
            value={input}
            onChange={event => setInput(event.target.value)}
            placeholder="Напишите боту…"
            aria-label="Сообщение для отправки в бот"
            className="flex-1 rounded-xl border border-border/60 bg-background px-3 py-2 text-sm shadow-inner outline-none focus:border-primary"
          />
          <Button type="submit" variant="primary" size="sm" disabled={sendMutation.isPending} aria-label="Отправить сообщение">
            {sendMutation.isPending ? <Loader2Icon className="mr-2 h-4 w-4 animate-spin" /> : <SendIcon className="mr-2 h-4 w-4" />}
            Отправить
          </Button>
        </form>
        {startAppLink && (
          <div className="rounded-xl border border-dashed border-primary/40 bg-primary/5 p-3 text-xs text-muted-foreground">
            Используйте Mini App: <span className="font-mono text-foreground">{startAppLink}</span>
          </div>
        )}
      </div>
    </div>
  )
}
