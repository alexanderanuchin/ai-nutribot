const ROUTE_PATTERNS: RegExp[] = [
  /^\/$/,
  /^\/feed(?:\/|$)/,
  /^\/plan(?:\/|$)/,
  /^\/search(?:\/|$)/,
  /^\/compose(?:\/|$)/,
  /^\/nutrition(?:\/|$)/,
  /^\/market(?:\/|$)/,
  /^\/notifications(?:\/|$)/,
  /^\/profile(?:\/|$)/,
  /^\/billing(?:\/|$)/,
  /^\/login(?:\/|$)/,
  /^\/register(?:\/|$)/,
  /^\/forgot-password(?:\/|$)/,
  /^\/reset-password(?:\/|$)/,
]

export const DEFAULT_BASE_PATH = '/'

function pickFirstCandidate(value?: string | null): string | undefined {
  if (!value) {
    return undefined
  }
  const normalised = value.replace(/\r?\n/g, ',').replace(/;/g, ',')
  for (const chunk of normalised.split(',')) {
    const candidate = chunk.trim()
    if (candidate) {
      return candidate
    }
  }
  return undefined
}

export function sanitizeBasePath(value?: string | null): string {
  const firstCandidate = pickFirstCandidate(value)
  if (!firstCandidate) {
    return DEFAULT_BASE_PATH
  }
  let candidate = firstCandidate
  if (candidate.includes('://')) {
    try {
      const url = new URL(candidate)
      candidate = url.pathname
    } catch {
      candidate = firstCandidate
    }
  }
  candidate = candidate.replace(/\\/g, '/')
  const stripped = candidate.replace(/\/+$/, '')
  if (!stripped) {
    return DEFAULT_BASE_PATH
  }
  return stripped.startsWith('/') ? stripped : `/${stripped}`
}

function normalizePathname(pathname: string): string {
  if (!pathname) {
    return DEFAULT_BASE_PATH
  }
  const withoutHash = pathname.split('#')[0]
  const withoutQuery = withoutHash.split('?')[0]
  const normalized = withoutQuery.trim()
  if (!normalized) {
    return DEFAULT_BASE_PATH
  }
  const ensured = normalized.startsWith('/') ? normalized : `/${normalized}`
  const collapsed = ensured.replace(/\/+$/, '')
  return collapsed || DEFAULT_BASE_PATH
}

function matchesKnownRoute(path: string): boolean {
  return ROUTE_PATTERNS.some(pattern => pattern.test(path))
}

export function inferBasePath(pathname: string): string {
  const normalized = normalizePathname(pathname)
  if (matchesKnownRoute(normalized)) {
    return DEFAULT_BASE_PATH
  }
  const segments = normalized.split('/').filter(Boolean)
  if (segments.length === 0) {
    return DEFAULT_BASE_PATH
  }
  return `/${segments[0]}`
}

export function resolveBasePath(
  pathname: string,
  envBase?: string | null,
  baseUrl?: string | null,
  compiledBase?: string | null,
): string {
  const envCandidate = sanitizeBasePath(envBase)
  if (envCandidate !== DEFAULT_BASE_PATH) {
    return envCandidate
  }
  const compiledCandidate = sanitizeBasePath(compiledBase)
  if (compiledCandidate !== DEFAULT_BASE_PATH) {
    return compiledCandidate
  }
  const baseUrlCandidate = sanitizeBasePath(baseUrl)
  if (baseUrlCandidate !== DEFAULT_BASE_PATH) {
    return baseUrlCandidate
  }
  return inferBasePath(pathname)
}

export function getAppBasePath(): string {
  const compiledBase = typeof __APP_BASE_PATH__ === 'string' ? __APP_BASE_PATH__ : undefined
  if (typeof window === 'undefined') {
    return resolveBasePath('/', import.meta.env.VITE_APP_BASE_PATH, import.meta.env.BASE_URL, compiledBase)
  }
  return resolveBasePath(window.location.pathname, import.meta.env.VITE_APP_BASE_PATH, import.meta.env.BASE_URL, compiledBase)
}

export function matchesKnownAppRoute(pathname: string): boolean {
  return matchesKnownRoute(normalizePathname(pathname))
}
