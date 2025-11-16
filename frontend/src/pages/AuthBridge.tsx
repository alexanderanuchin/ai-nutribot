import { useEffect } from 'react'
import { bootstrapTelegramAuth, tg } from '../lib/telegram'
import { debugLog, generateRequestId, warnLog } from '../lib/logging'
import { sendApplicationLog } from '../lib/monitoring'
import { tokenStore } from '../utils/storage'

export default function AuthBridge() {
  useEffect(() => {
    const rid = generateRequestId()
    const webApp = tg()
    const sendAuthPayload = async () => {
      try {
        const session = await bootstrapTelegramAuth()
        const accessToken = session?.accessToken || tokenStore.access
        if (!accessToken) {
          warnLog('telegram/bridge', 'no access token available', { rid })
          void sendApplicationLog({
            level: 'WARNING',
            logger: 'webapp.telegram.auth',
            message: 'bridge missing token',
            requestId: rid,
            extra: { hasSession: Boolean(session) },
          })
            return
        }
        const refreshToken = session?.refreshToken || tokenStore.refresh || undefined
        const expiresAt = session?.expiresAt ?? tokenStore.accessExpiresAt
        const userId = webApp?.initDataUnsafe?.user?.id
        const payload = {
          type: 'auth',
          access_token: accessToken,
          refresh_token: refreshToken ?? undefined,
          expires_at: expiresAt ?? undefined,
          exp: expiresAt ?? undefined,
          user_id: userId ?? undefined,
          rid,
          reason: 'bridge',
        }
        debugLog('telegram/bridge', 'sending auth payload', {
          rid,
          hasRefresh: Boolean(refreshToken),
          expiresAt,
          userId,
          hasWebApp: Boolean(webApp?.sendData),
        })
        void sendApplicationLog({
          level: 'INFO',
          logger: 'webapp.telegram.sendData',
          message: 'auth payload sent',
          requestId: rid,
          extra: {
            reason: 'bridge',
            hasAccess: Boolean(accessToken),
            userId,
            expiresAt,
            hasWebApp: Boolean(webApp?.sendData),
          },
        })
        webApp?.sendData?.(JSON.stringify(payload))
        void sendApplicationLog({
          level: 'INFO',
          logger: 'webapp.telegram.sendData',
          message: 'auth payload delivered',
          requestId: rid,
          extra: {
            reason: 'bridge',
            hasAccess: Boolean(accessToken),
            userId,
            hasWebApp: Boolean(webApp?.sendData),
          },
        })
      } catch (error) {
        warnLog('telegram/bridge', 'sendData failed', {
          rid,
          error: error instanceof Error ? error.message : String(error),
        })
        void sendApplicationLog({
          level: 'WARNING',
          logger: 'webapp.telegram.sendData',
          message: 'auth payload failed',
          requestId: rid,
          extra: {
            reason: 'bridge',
            hasWebApp: Boolean(webApp?.sendData),
            error: error instanceof Error ? error.message : String(error),
          },
        })
      } finally {
        try {
          webApp?.close?.()
        } catch {}
      }
    }

    void sendAuthPayload()
  }, [])

  return null
}
