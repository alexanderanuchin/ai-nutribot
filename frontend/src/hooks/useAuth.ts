import { useEffect, useState } from 'react'
import { tokenStore } from '../utils/storage'

export function useAuth(){
  const [ready, setReady] = useState(false)
  const [authenticated, setAuthenticated] = useState<boolean>(!!tokenStore.access)
  useEffect(() => { setAuthenticated(!!tokenStore.access); setReady(true) }, [])
  return { ready, authenticated }
}
