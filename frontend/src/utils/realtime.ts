export function resolveRealtimeHttpBase(): string {
  const base = (import.meta.env.VITE_API_BASE || '/api') as string
  if (base.startsWith('http')) {
    return base.replace(/\/$/, '')
  }
  if (typeof window === 'undefined') {
    return base.replace(/\/$/, '')
  }
  if (base.startsWith('/')) {
    return `${window.location.origin}${base}`.replace(/\/$/, '')
  }
  return `${window.location.origin}/${base}`.replace(/\/$/, '')
}

export function resolveRealtimeWsBase(): string {
  const custom = (import.meta.env as any)?.VITE_WS_BASE as string | undefined
  if (custom && typeof custom === 'string') {
    return custom.replace(/\/$/, '')
  }
  if (typeof window === 'undefined') {
    return 'ws://localhost'
  }
  const { protocol, host } = window.location
  const scheme = protocol === 'https:' ? 'wss:' : 'ws:'
  return `${scheme}//${host}`
}