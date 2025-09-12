import { useEffect } from 'react'
import { getInitData } from '../lib/telegram'
import api from '../api/client'
import { tokenStore } from '../utils/storage'

export function useTelegramAuth(){
  useEffect(() => {
    const initData = getInitData()
    if (!initData) return
    ;(async () => {
      try{
        const { data } = await api.post('/users/auth/tg_exchange/', { init_data: initData })
        tokenStore.access = data.access
        tokenStore.refresh = data.refresh
      }catch{ /* ignore */ }
    })()
  }, [])
}
