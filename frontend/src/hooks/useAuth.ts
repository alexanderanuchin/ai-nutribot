import { useEffect, useState } from 'react'
import {  AUTH_CHANGE_EVENT, tokenStore } from '../utils/storage'

export function useAuth(){
  const [ready, setReady] = useState(false)
  const [authenticated, setAuthenticated] = useState<boolean>(!!tokenStore.access)
  useEffect(() => {
    const syncAuthState = () => setAuthenticated(!!tokenStore.access)
    syncAuthState()
    setReady(true)
    window.addEventListener(AUTH_CHANGE_EVENT, syncAuthState)
    window.addEventListener('storage', syncAuthState)
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, syncAuthState)
      window.removeEventListener('storage', syncAuthState)
    }
  }, [])
  return { ready, authenticated }
}
