import { refreshAccessToken } from '../api/client'
import { tokenStore } from './storage'

const DEFAULT_MIN_TTL_SECONDS = 60

export async function ensureFreshAccessToken(minTtlSeconds = DEFAULT_MIN_TTL_SECONDS): Promise<string | null> {
  const access = tokenStore.access
  if (!access) {
    return null
  }

  const nowSec = Math.floor(Date.now() / 1000)
  const expiresAt = tokenStore.accessExpiresAt
  const ttl = typeof expiresAt === 'number' ? expiresAt - nowSec : null
  const shouldRefresh = typeof ttl === 'number' ? ttl <= minTtlSeconds : false

  if (!shouldRefresh) {
    return access
  }

  try {
    const refreshed = await refreshAccessToken()
    if (typeof refreshed === 'string' && refreshed) {
      return refreshed
    }
    return tokenStore.access || null
  } catch (error) {
    console.warn('ensureFreshAccessToken: failed to refresh access token', error)
    return tokenStore.access || null
  }
}
