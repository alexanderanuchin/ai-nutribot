import api from '../api/client'
import { tokenStore } from '../utils/storage'

export function tg(){ return (window as any).Telegram?.WebApp }
export function initTheme(){
  const w = tg()
  if (w){ w.ready(); document.body.style.background = w.themeParams?.bg_color || '#0b0c10' }
}
export function getInitData(): string | null {
  const w = tg()
  return w?.initData || null
}

export interface TelegramAuthSession {
  accessToken: string
  refreshToken?: string
  telegramUserId: number | null
  raw: any
}

let bootstrapPromise: Promise<TelegramAuthSession | null> | null = null

export async function bootstrapTelegramAuth(): Promise<TelegramAuthSession | null> {
  if (bootstrapPromise) return bootstrapPromise
  const initData = getInitData()
  if (!initData) return null

  bootstrapPromise = (async () => {
    try {
      const { data } = await api.post('/auth/webapp/login/', { init_data: initData })
      if (!data?.access) {
        throw new Error('Не удалось получить access_token')
      }
      tokenStore.access = data.access
      tokenStore.refresh = data.refresh ?? ''

      const telegramUserId: number | null =
        data?.telegram_user_id ??
        data?.profile?.telegram_id ??
        data?.user?.telegram_id ??
        data?.user?.id ??
        null

      return {
        accessToken: data.access as string,
        refreshToken: data.refresh as string | undefined,
        telegramUserId,
        raw: data,
      }
    } catch (err) {
      console.error('Не удалось обменять initData на токены', err)
      throw err
    }
  })()

  try {
    return await bootstrapPromise
  } finally {
    bootstrapPromise = null
  }
}