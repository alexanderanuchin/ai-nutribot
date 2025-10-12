const DEBUG_LOGS = import.meta.env.VITE_DEBUG_LOGS === '1'

export function maskToken(token: string | null | undefined): string {
  if (!token) return 'present=false'
  const prefix = token.slice(0, 4)
  return `present=true prefix=${prefix}*** len=${token.length}`
}

export function debugLog(scope: string, message: string, details?: Record<string, unknown>): void {
  if (!DEBUG_LOGS) return
  if (details) {
    console.info(`[${scope}] ${message}`, details)
  } else {
    console.info(`[${scope}] ${message}`)
  }
}

export function warnLog(scope: string, message: string, details?: Record<string, unknown>): void {
  if (!DEBUG_LOGS) return
  if (details) {
    console.warn(`[${scope}] ${message}`, details)
  } else {
    console.warn(`[${scope}] ${message}`)
  }
}

export function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`
}

export function isDebugLogsEnabled(): boolean {
  return DEBUG_LOGS
}