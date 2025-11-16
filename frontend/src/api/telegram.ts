import api from './client'

export interface TelegramLinkResponse {
  code: string
  expires_at: string
  links: {
    tg: string
    tme: string
    startapp: string
  }
}

export interface TelegramStatusResponse {
  linked: boolean
  telegram_id?: number | null
  telegram_username?: string | null
  app_username?: string | null
  linked_at?: string | null
  link: TelegramLinkResponse
}

export function fetchTelegramStatus() {
  return api.get<TelegramStatusResponse>('/users/integrations/telegram/status/').then(res => res.data)
}

export function startTelegramLink() {
  return api.post<TelegramLinkResponse>('/users/integrations/telegram/link/start/').then(res => res.data)
}

export function sendBridgeMessage(text: string, clientId?: string) {
  return api.post('/users/telegram/bridge/send/', { text, client_id: clientId }).then(res => res.data)
}
