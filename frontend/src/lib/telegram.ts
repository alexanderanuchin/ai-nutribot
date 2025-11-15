import api from '../api/client'
import { tokenStore } from '../utils/storage'
import { debugLog, generateRequestId, maskToken, warnLog } from './logging'
import { sendApplicationLog } from './monitoring'

export function tg() {
  return (window as any).Telegram?.WebApp
}

const MIN_VERTICAL_SWIPE_CONTROL_VERSION = '6.1'

function parseVersionParts(version: string): number[] {
  return version
    .split('.')
    .map((part) => {
      const parsed = Number.parseInt(part, 10)
      return Number.isNaN(parsed) ? 0 : parsed
    })
}

function compareVersionStrings(current: string, minimum: string): number {
  const currentParts = parseVersionParts(current)
  const minimumParts = parseVersionParts(minimum)
  const maxLength = Math.max(currentParts.length, minimumParts.length)
  for (let index = 0; index < maxLength; index += 1) {
    const currentValue = currentParts[index] ?? 0
    const minimumValue = minimumParts[index] ?? 0
    if (currentValue > minimumValue) return 1
    if (currentValue < minimumValue) return -1
  }
  return 0
}

export function supportsVerticalSwipeControl(webApp = tg()): boolean {
  if (!webApp) return false
  const hasControlMethods =
    typeof webApp.disableVerticalSwipes === 'function' && typeof webApp.enableVerticalSwipes === 'function'
  if (!hasControlMethods) {
    return false
  }
  if (typeof webApp.isVersionAtLeast === 'function') {
    try {
      return webApp.isVersionAtLeast(MIN_VERTICAL_SWIPE_CONTROL_VERSION)
    } catch {}
  }
  const version = typeof webApp.version === 'string' ? webApp.version : ''
  if (!version) {
    return false
  }
  return compareVersionStrings(version, MIN_VERTICAL_SWIPE_CONTROL_VERSION) >= 0
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

function getTelegramUserIdFromSdk(): number | null {
  const webApp = tg()
  const rawId = webApp?.initDataUnsafe?.user?.id
  return typeof rawId === 'number' ? rawId : null
}

function logWebAppEnvironment(initData: string | null): void {
  if (typeof window === 'undefined') return
  const rid = generateRequestId()
  const webApp = tg()
  const hasTelegram = Boolean(webApp)
  const length = initData?.length ?? 0
  const preview = initData ? initData.slice(0, 16) : ''
  const url = window.location.href
  const payload = {
    hasTelegram,
    initDataLength: length,
    initDataPreview: preview,
    url,
  }
  debugLog('telegram/env', 'environment detection', payload)
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.telegram.environment',
    message: 'webapp bootstrap environment',
    requestId: rid,
    extra: payload,
  })
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
  const body = { init_data: initData }
  const { data } = await api.post('/auth/webapp/login/', body, { headers })
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
  const telegramUserIdFromBackend = resolveTelegramUserId(data)
  const telegramUserIdFromSdk = getTelegramUserIdFromSdk()
  const session: TelegramAuthSession = {
    accessToken: access,
    refreshToken,
    telegramUserId: telegramUserIdFromSdk ?? telegramUserIdFromBackend,
    expiresAt: expiresAt ?? tokenStore.accessExpiresAt,
    raw: data,
  }

  debugLog('telegram/auth', 'login success', {
    rid,
    telegramUserIdFromBackend,
    telegramUserIdFromSdk,
    expiresAt: session.expiresAt,
    hasRefresh: Boolean(refreshToken),
  })
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.telegram.auth',
    message: 'login success',
    requestId: rid,
    extra: {
      telegramUserId: session.telegramUserId,
      telegramUserIdFromBackend,
      expiresAt: session.expiresAt,
      hasRefresh: Boolean(refreshToken),
    },
  })
  sendAuthPayloadToBot({
    accessToken: access,
    refreshToken,
    expiresAt: session.expiresAt,
    rid,
    reason: 'login',
  })

  return session
}

interface AuthPayload {
  accessToken: string
  refreshToken?: string
  expiresAt?: number | null
  rid: string
  reason: 'login' | 'rehydrate'
}

function sendAuthPayloadToBot({ accessToken, refreshToken, expiresAt, rid, reason }: AuthPayload): void {
  const webApp = tg()
  if (!webApp || typeof webApp.sendData !== 'function') {
    debugLog('telegram/sendData', 'skip auth payload', {
      rid,
      reason,
      hasWebApp: Boolean(webApp),
    })
    return
  }
  const telegramUserId = getTelegramUserIdFromSdk()
  try {
    debugLog('telegram/sendData', 'auth payload', {
      rid,
      reason,
      telegramUserId,
      expiresAt,
    })
    void sendApplicationLog({
      level: 'INFO',
      logger: 'webapp.telegram.sendData',
      message: 'auth payload sent',
      requestId: rid,
      extra: {
        reason,
        telegramUserId,
        expiresAt,
      },
    })
    webApp.sendData(
      JSON.stringify({
        type: 'auth',
        access_token: accessToken,
        refresh_token: refreshToken ?? undefined,
        expires_at: expiresAt ?? undefined,
        user_id: telegramUserId ?? undefined,
        rid,
      })
    )
  } catch (error) {
    warnLog('telegram/sendData', 'auth payload failed', {
      rid,
      reason,
      error: error instanceof Error ? error.message : String(error),
    })
    void sendApplicationLog({
      level: 'WARNING',
      logger: 'webapp.telegram.sendData',
      message: 'auth payload failed',
      requestId: rid,
      extra: {
        reason,
        error: error instanceof Error ? error.message : String(error),
      },
    })
  }
}

function rehydrateBotSession(): void {
  const accessToken = tokenStore.access
  if (!accessToken) {
    return
  }
  const rid = generateRequestId()
  sendAuthPayloadToBot({
    accessToken,
    refreshToken: tokenStore.refresh || undefined,
    expiresAt: tokenStore.accessExpiresAt,
    rid,
    reason: 'rehydrate',
  })
}

export async function bootstrapTelegramAuth(): Promise<TelegramAuthSession | null> {
  if (cachedSession !== undefined) {
    if (shouldReuseSession(cachedSession)) {
      rehydrateBotSession()
      return cachedSession
    }
    cachedSession = undefined
  }
  if (bootstrapPromise) {
    return bootstrapPromise
  }

  const initData = getInitData()
  logWebAppEnvironment(initData)
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