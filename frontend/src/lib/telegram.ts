import api from '../api/client'
import { tokenStore } from '../utils/storage'
import { debugLog, generateRequestId, maskToken, warnLog } from './logging'
import { sendApplicationLog } from './monitoring'

export function tg() {
  return (window as any).Telegram?.WebApp
}

export function initTheme() {
  const webApp = tg()
  if (webApp) {
    webApp.ready()
    document.body.style.background = webApp.themeParams?.bg_color || '#0b0c10'
  }
}

export function getInitData(): string | null {
  const webApp = tg()
  return webApp?.initData || null
}

export interface TelegramAuthSession {
  accessToken: string
  refreshToken?: string
  telegramUserId: number | null
  expiresAt?: number | null
  raw: any
}

let bootstrapPromise: Promise<TelegramAuthSession | null> | null = null
let cachedSession: TelegramAuthSession | null | undefined

function shouldReuseSession(session: TelegramAuthSession | null | undefined): boolean {
  if (!session) {
    return false
  }
  const access = tokenStore.access
  if (!access) {
    return false
  }
  const expiresAt = session.expiresAt ?? tokenStore.accessExpiresAt
  if (!expiresAt) {
    return true
  }
  const nowSeconds = Math.floor(Date.now() / 1000)
  const safetyWindowSeconds = 45
  return expiresAt - nowSeconds > safetyWindowSeconds
}

function resolveTelegramUserId(payload: any): number | null {
  if (!payload || typeof payload !== 'object') return null
  const direct = payload.telegram_user_id ?? payload.telegramUserId
  if (typeof direct === 'number') return direct
  const fromProfile = payload.profile?.telegram_id ?? payload.profile?.telegramId
  if (typeof fromProfile === 'number') return fromProfile
  const fromUser = payload.user?.telegram_id ?? payload.user?.id
  if (typeof fromUser === 'number') return fromUser
  return null
}

async function exchangeInitData(initData: string): Promise<TelegramAuthSession | null> {
  const headers = { 'X-Telegram-Init-Data': initData }
  const rid = generateRequestId()
  headers['X-Request-Id'] = rid
  debugLog('telegram/auth', 'login request', {
    rid,
    hasInitData: Boolean(initData),
    initData: maskToken(initData),
  })
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.telegram.auth',
    message: 'login request',
    requestId: rid,
    extra: {
      hasInitData: Boolean(initData),
    },
  })
  const { data } = await api.post('/auth/webapp/login/', {}, { headers })
  const access = data?.access
  if (!access || typeof access !== 'string') {
    throw new Error('Не удалось получить access_token из ответа авторизации')
  }
  const refreshToken: string | undefined = typeof data?.refresh === 'string' ? data.refresh : undefined
  if (refreshToken) {
    tokenStore.refresh = refreshToken
  }
  tokenStore.access = access
  const expiresAt: number | undefined = typeof data?.exp === 'number' ? data.exp : undefined
  if (expiresAt) {
    tokenStore.accessExpiresAt = expiresAt
  }
  const telegramUserId = resolveTelegramUserId(data)
  const session: TelegramAuthSession = {
    accessToken: access,
    refreshToken,
    telegramUserId,
    expiresAt: expiresAt ?? tokenStore.accessExpiresAt,
    raw: data,
  }

  debugLog('telegram/auth', 'login success', {
    rid,
    telegramUserId,
    expiresAt: session.expiresAt,
    hasRefresh: Boolean(refreshToken),
  })
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.telegram.auth',
    message: 'login success',
    requestId: rid,
    extra: {
      telegramUserId,
      expiresAt: session.expiresAt,
      hasRefresh: Boolean(refreshToken),
    },
  })
  const webApp = tg()
  if (webApp && typeof webApp.sendData === 'function') {
    try {
      debugLog('telegram/sendData', 'auth payload', {
        rid,
        telegramUserId,
        expiresAt,
      })
      void sendApplicationLog({
        level: 'INFO',
        logger: 'webapp.telegram.sendData',
        message: 'auth payload sent',
        requestId: rid,
        extra: {
          telegramUserId,
          expiresAt,
        },
      })
      webApp.sendData(
        JSON.stringify({
          type: 'auth',
          access_token: access,
          refresh_token: refreshToken ?? undefined,
          expires_at: expiresAt ?? undefined,
          user_id: telegramUserId ?? undefined,
          rid,
        })
      )
    } catch (error) {
      warnLog('telegram/sendData', 'auth payload failed', {
        rid,
        error: error instanceof Error ? error.message : String(error),
      })
      void sendApplicationLog({
        level: 'WARNING',
        logger: 'webapp.telegram.sendData',
        message: 'auth payload failed',
        requestId: rid,
        extra: {
          error: error instanceof Error ? error.message : String(error),
        },
      })
    }
  }

  return session
}

export async function bootstrapTelegramAuth(): Promise<TelegramAuthSession | null> {
  if (cachedSession !== undefined) {
    if (shouldReuseSession(cachedSession)) {
      return cachedSession
    }
    cachedSession = undefined
  }
  if (bootstrapPromise) {
    return bootstrapPromise
  }

  const initData = getInitData()
  if (!initData) {
    cachedSession = null
    return cachedSession
  }

  bootstrapPromise = exchangeInitData(initData)
    .then(session => {
      cachedSession = session
      return session
    })
    .catch(error => {
      warnLog('telegram/auth', 'login failed', {
        error: error instanceof Error ? error.message : String(error),
      })
      void sendApplicationLog({
        level: 'WARNING',
        logger: 'webapp.telegram.auth',
        message: 'login failed',
        extra: {
          error: error instanceof Error ? error.message : String(error),
        },
      })
      cachedSession = null
      throw error
    })
    .finally(() => {
      bootstrapPromise = null
    })

  return bootstrapPromise
}