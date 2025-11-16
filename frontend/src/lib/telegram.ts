import api from '../api/client'
import { tokenStore } from '../utils/storage'
import { debugLog, generateRequestId, maskToken, warnLog } from './logging'
import { sendApplicationLog } from './monitoring'

export function tg() {
  return (window as any).Telegram?.WebApp
}

export function isTgWebAppPresent(): boolean {
  return typeof window !== 'undefined' && Boolean((window as any).Telegram?.WebApp)
}

function hasValidInitData(rawInitData: string | null): boolean {
  if (!rawInitData || typeof rawInitData !== 'string') return false
  try {
    const params = new URLSearchParams(rawInitData)
    return Boolean(params.get('hash') && (params.get('user') || params.get('chat_instance')))
  } catch {
    return false
  }
}

export function isTgWebAppRuntime(): boolean {
  if (typeof window === 'undefined') return false
  const webApp = tg()
  if (!webApp) return false
  return hasValidInitData(getInitData())
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
    hasInitData: Boolean(initData),
    hasSendData: Boolean(webApp?.sendData),
  }
  debugLog('telegram/env', 'environment detection', payload)
  void sendApplicationLog({
    level: 'INFO',
    logger: 'webapp.telegram.environment',
    message: 'webapp bootstrap environment',
    requestId: rid,
    extra: { ...payload, rid },
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
let rehydrateOnceGuard = false
let manualBridgeTimeout: ReturnType<typeof setTimeout> | null = null
let manualBridgeActive = false
let manualBridgeClickHandler: (() => void) | null = null
let lastSendDataAttempt: { rid: string; status: 'sent' | 'skipped' | 'failed'; reason?: string; timestamp: number } | null = null

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
      phase: 'start',
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
      hasAccess: Boolean(access),
      phase: 'success',
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
  reason: 'login' | 'rehydrate' | 'bridge' | 'manual'
}

function resetManualBridge(mainButton: any) {
  if (!mainButton) return
  if (typeof mainButton.offClick === 'function' && manualBridgeClickHandler) {
    mainButton.offClick(manualBridgeClickHandler)
  }
  manualBridgeClickHandler = null
  manualBridgeActive = false
  try {
    mainButton.hide?.()
  } catch {}
}

function scheduleManualBridge(payload: AuthPayload & { userId?: number | null }) {
  const webApp = tg()
  const mainButton = webApp?.MainButton
  if (!mainButton || manualBridgeTimeout || manualBridgeActive) {
    return
  }
  manualBridgeTimeout = setTimeout(() => {
    manualBridgeTimeout = null
    if (!webApp?.MainButton) return
    const targetButton = webApp.MainButton
    manualBridgeActive = true
    targetButton.setText?.('Связать с ботом')
    manualBridgeClickHandler = () => {
      sendAuthPayloadToBot({ ...payload, rid: generateRequestId(), reason: 'manual' })
      try {
        webApp.close?.()
      } catch {}
      resetManualBridge(targetButton)
    }
    if (typeof targetButton.onClick === 'function' && manualBridgeClickHandler) {
      targetButton.onClick(manualBridgeClickHandler)
    }
    targetButton.show?.()
  }, 1500)
}

function sendAuthPayloadToBot({ accessToken, refreshToken, expiresAt, rid, reason }: AuthPayload): boolean {
  const webApp = tg()
  if (!webApp || typeof webApp.sendData !== 'function') {
    lastSendDataAttempt = { rid, status: 'skipped', reason: 'missing-webapp', timestamp: Date.now() }
    debugLog('telegram/sendData', 'skip auth payload', {
      rid,
      reason,
      hasWebApp: Boolean(webApp),
    })
    scheduleManualBridge({
      accessToken,
      refreshToken,
      expiresAt: expiresAt ?? undefined,
      rid,
      reason,
      userId: undefined,
    })
    return false
  }
  const telegramUserId = getTelegramUserIdFromSdk()
  try {
    debugLog('telegram/sendData', 'auth payload', {
      rid,
      reason,
      telegramUserId,
      expiresAt,
      hasAccess: Boolean(accessToken),
      hasWebApp: Boolean(webApp?.sendData),
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
        hasAccess: Boolean(accessToken),
        hasWebApp: Boolean(webApp?.sendData),
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
    lastSendDataAttempt = { rid, status: 'sent', reason, timestamp: Date.now() }
    if (manualBridgeTimeout) {
      clearTimeout(manualBridgeTimeout)
      manualBridgeTimeout = null
    }
    if (manualBridgeActive) {
      resetManualBridge(webApp.MainButton)
    }
    return true
  } catch (error) {
    warnLog('telegram/sendData', 'auth payload failed', {
      rid,
      reason,
      error: error instanceof Error ? error.message : String(error),
    })
    lastSendDataAttempt = { rid, status: 'failed', reason, timestamp: Date.now() }
    void sendApplicationLog({
      level: 'WARNING',
      logger: 'webapp.telegram.sendData',
      message: 'auth payload failed',
      requestId: rid,
      extra: {
        reason,
        hasAccess: Boolean(accessToken),
        hasWebApp: Boolean(webApp?.sendData),
        error: error instanceof Error ? error.message : String(error),
      },
    })
    scheduleManualBridge({
      accessToken,
      refreshToken,
      expiresAt: expiresAt ?? undefined,
      rid,
      reason,
      userId: telegramUserId,
    })
    return false
  }
}

export function rehydrateBotSession(): void {
  if (rehydrateOnceGuard) return
  if (!isTgWebAppRuntime()) return
  const accessToken = tokenStore.access
  const expiresAt = tokenStore.accessExpiresAt
  if (!accessToken) {
    return
  }
  if (typeof expiresAt === 'number') {
    const nowSeconds = Math.floor(Date.now() / 1000)
    const safetySeconds = 15
    if (expiresAt <= nowSeconds + safetySeconds) {
      return
    }
  }

  rehydrateOnceGuard = true
  const rid = generateRequestId()
  sendAuthPayloadToBot({
    accessToken,
    refreshToken: tokenStore.refresh || undefined,
    expiresAt,
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
    void sendApplicationLog({
      level: 'WARNING',
      logger: 'webapp.telegram.auth',
      message: 'init data missing',
      requestId: generateRequestId(),
      extra: { hasTelegram: Boolean(tg()) },
    })
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
          phase: 'fail',
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

export function openTelegramLink(url: string): void {
  const webApp = tg()
  if (webApp?.openTelegramLink) {
    webApp.openTelegramLink(url)
    return
  }
  window.open(url, '_blank', 'noopener')
}

export function getLastSendDataAttempt() {
  return lastSendDataAttempt
}