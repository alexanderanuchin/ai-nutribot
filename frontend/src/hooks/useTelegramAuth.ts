import { useEffect } from 'react'
import { bootstrapTelegramAuth } from '../lib/telegram'

export function useTelegramAuth(){
  useEffect(() => {
    void bootstrapTelegramAuth().catch(() => undefined)
  }, [])
}
