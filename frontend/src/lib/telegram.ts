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

function hasValidInitData(raw: string | null): boolean {
  if (!raw) return false
  try {
    const params = new URLSearchParams(raw)
    return Boolean(params.get('hash') && (params.get('user') || params.get('chat_instance')))
  } catch {
    return false
  }
}

export function getInitData(): string | null {
  try {
    const runtimeInitData = tg()?.initData || null
    if (hasValidInitData(runtimeInitData)) {
      return runtimeInitData
    }

    if (typeof window === 'undefined') return runtimeInitData

    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const fromHash = hashParams.get('tgWebAppData')
    if (hasValidInitData(fromHash)) {
      return fromHash
    }

    const searchParams = new URLSearchParams(window.location.search)
    const fromQuery = searchParams.get('tgWebAppData')
    if (hasValidInitData(fromQuery)) {
      return fromQuery
    }

    return runtimeInitData || fromHash || fromQuery
  } catch {
    return null
  }
}

export function isTgWebAppRuntime(): boolean {
  return typeof window !== 'undefined' && Boolean(tg()) && hasValidInitData(getInitData())
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

export async function runAuthBridge(payloadForStartApp = 'auth') {
  const rid = generateRequestId()
  if (!isTgWebAppRuntime()) {
    const { buildStartAppLink } = await import('./deeplinks')
    const startAppLink = buildStartAppLink(payloadForStartApp)
    debugLog('telegram/bridge', 'redirecting to startapp deeplink', { rid, startAppLink })
    window.location.href = startAppLink
    return
  }

  const initData = getInitData()
  if (!hasValidInitData(initData)) {
    warnLog('telegram/bridge', 'missing or invalid initData in Mini App runtime', {
      rid,
      hasInitData: Boolean(initData),
    })
    return
  }

  const session = await exchangeInitData(initData)
  await sendAuthPayloadToTelegram(session, rid)

  // Не закрываем WebView насильно: на десктопных клиентах закрытие происходит раньше, чем отрисуется контент.
  window.location.href = '/app'
}

export interface TelegramAuthSession {
  accessToken?: string
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
  const rid = generateRequestId()
  const headers: Record<string, string> = { 'X-Request-Id': rid }
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData
  }
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
  const access: string | undefined = typeof data?.access === 'string' ? data.access : undefined
  const refreshToken: string | undefined = typeof data?.refresh === 'string' ? data.refresh : undefined
  const expiresAt: number | undefined = typeof data?.exp === 'number' ? data.exp : undefined

  if (access) {
    tokenStore.access = access
  }
  if (refreshToken) {
    tokenStore.refresh = refreshToken
  }
  if (expiresAt) {
    tokenStore.accessExpiresAt = expiresAt
  }
  const telegramUserIdFromBackend = resolveTelegramUserId(data)
  const telegramUserIdFromSdk = getTelegramUserIdFromSdk()
  const session: TelegramAuthSession = {
    accessToken: access ?? tokenStore.access,
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
    hasAccess: Boolean(access ?? tokenStore.access),
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

function shouldCloseWebViewFromParams(): boolean {
  if (typeof window === 'undefined') return false
  const params = new URLSearchParams(window.location.search)
  const closeParam = params.get('close') || params.get('webapp_close')
  if (!closeParam) return false
  return ['1', 'true', 'yes', 'on', 'y'].includes(closeParam.toLowerCase())
}

async function sendAuthPayloadToTelegram(
  session: TelegramAuthSession | null,
  rid: string,
): Promise<void> {
  const webApp = tg()
  if (!webApp || typeof webApp.sendData !== 'function') {
    debugLog('telegram/sendData', 'skip sendData', {
      rid,
      hasWebApp: Boolean(webApp),
      hasSession: Boolean(session),
      canSend: Boolean(webApp?.sendData),
    })
    return
  }

  const access = session?.accessToken ?? tokenStore.access ?? ''
  const refresh = session?.refreshToken ?? tokenStore.refresh ?? ''
  const expiresAt = session?.expiresAt ?? tokenStore.accessExpiresAt ?? null

  if (!access && !refresh) {
    debugLog('telegram/sendData', 'skip sendData missing tokens', {
      rid,
      hasSession: Boolean(session),
      hasAccess: Boolean(access),
      hasRefresh: Boolean(refresh),
    })
    return
  }

  const payload = {
    type: 'auth',
    access_token: access,
    refresh_token: refresh,
    // compatibility for handlers expecting legacy keys
    access,
    refresh,
    expires_at: expiresAt,
    rid,
  }

  try {
    webApp.sendData(JSON.stringify(payload))
    debugLog('telegram/sendData', 'auth payload sent to bot', {
      rid,
      hasRefresh: Boolean(refresh),
      hasAccess: Boolean(access),
    })
    void sendApplicationLog({
      level: 'INFO',
      logger: 'webapp.telegram.auth',
      message: 'sendData auth payload sent',
      requestId: rid,
      extra: {
        hasRefresh: Boolean(refresh),
        hasAccess: Boolean(access),
        expiresAt,
        phase: 'sendData',
      },
    })
    await new Promise(resolve => setTimeout(resolve, 150))
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    warnLog('telegram/sendData', 'failed to send auth payload', { rid, error: message })
    void sendApplicationLog({
      level: 'WARNING',
      logger: 'webapp.telegram.auth',
      message: 'sendData auth payload failed',
      requestId: rid,
      extra: {
        error: message,
        phase: 'sendData_failed',
      },
    })
  }

  if (shouldCloseWebViewFromParams()) {
    try {
      webApp.close()
      debugLog('telegram/sendData', 'webapp closed by query flag', { rid })
    } catch (error) {
      warnLog('telegram/sendData', 'failed to close webapp', {
        rid,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }
}

export function openTelegramLink(url: string): void {
  const webApp = tg()
  if (webApp?.openTelegramLink) {
    webApp.openTelegramLink(url)
    return
  }
  window.open(url, '_blank', 'noopener')
}