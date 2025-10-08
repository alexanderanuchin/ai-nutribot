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

let bootstrapPromise: Promise<void> | null = null

export async function bootstrapTelegramAuth(): Promise<void> {
  if (bootstrapPromise) return bootstrapPromise
  const initData = getInitData()
  if (!initData) return

  bootstrapPromise = (async () => {
    try {
      const { data } = await api.post('/users/auth/tg_exchange/', { init_data: initData })
      tokenStore.access = data.access
      tokenStore.refresh = data.refresh

      const webApp = tg()
      if (webApp && data.access) {
        try {
          webApp.sendData(JSON.stringify({ access_token: data.access }))
        } catch (err) {
          console.error('Не удалось отправить access_token в бота через sendData', err)
        }
      }
    } catch (err) {
      console.error('Не удалось обменять initData на токены', err)
      throw err
    }
  })()

  try {
    await bootstrapPromise
  } finally {
    bootstrapPromise = null
  }
}