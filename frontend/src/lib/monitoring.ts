import { tokenStore } from '../utils/storage'
import { generateRequestId, isDebugLogsEnabled } from './logging'

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')
const MONITORING_ENDPOINT = `${API_BASE}/monitoring/application/logs/`

type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

interface RemoteLogPayload {
  level: LogLevel
  message: string
  requestId?: string
  logger?: string
  extra?: Record<string, unknown>
  group?: 'application' | 'administrative'
  excText?: string
}

async function postLog(payload: RemoteLogPayload): Promise<void> {
  if (typeof fetch === 'undefined') return
  const rid = payload.requestId || generateRequestId()
  const body = {
    level: payload.level,
    message: payload.message,
    request_id: rid,
    logger: payload.logger,
    extra: payload.extra,
    group: payload.group,
    exc_text: payload.excText,
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Request-Id': rid,
  }

  const access = tokenStore.access
  if (access) {
    headers.Authorization = `Bearer ${access}`
  }
  const initData = resolveInitData()
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }

  try {
    await fetch(MONITORING_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify(body),
      headers,
      keepalive: true,
    })
  } catch (error) {
    if (isDebugLogsEnabled()) {
      console.warn('Failed to send monitoring log', error)
    }
  }
}

export async function sendApplicationLog(payload: RemoteLogPayload): Promise<void> {
  if (typeof window === 'undefined') return
  await postLog(payload)
}

function resolveInitData(): string | null {
  if (typeof window === 'undefined') return null
  const telegram = (window as any)?.Telegram?.WebApp
  return telegram?.initData || null
}