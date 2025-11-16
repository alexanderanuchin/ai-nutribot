import { useEffect } from 'react'
import { fetchTelegramStatus } from '../api/telegram'
import { runAuthBridge } from '../lib/telegram'
import { generateRequestId, warnLog } from '../lib/logging'
import { sendApplicationLog } from '../lib/monitoring'

export default function AuthBridge() {
  useEffect(() => {
    const rid = generateRequestId()
    const execute = async () => {
      try {
        const status = await fetchTelegramStatus().catch(() => null)
        const payload = status?.link?.code || 'auth'
        await runAuthBridge(payload)
      } catch (error) {
        warnLog('telegram/bridge', 'auth bridge failed', {
          rid,
          error: error instanceof Error ? error.message : String(error),
        })
        void sendApplicationLog({
          level: 'WARNING',
          logger: 'webapp.telegram.bridge',
          message: 'auth bridge failed',
          requestId: rid,
          extra: {
            error: error instanceof Error ? error.message : String(error),
          },
        })
      }
    }

    void execute()
  }, [])

  return null
}
