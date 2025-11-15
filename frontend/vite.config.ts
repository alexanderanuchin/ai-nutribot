// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Минимум, чтобы Vite работал через CloudPub/Caloiq домены, не ломая твою логику.
// PUBLIC_BASE_HOST можно задать в .env (например, https://caloiq.ru).
const DEFAULT_PUBLISHED_HOST = 'caloiq.ru'

const splitCandidates = (value: string | undefined): string[] => {
  if (!value) {
    return []
  }
  return value
    .replace(/\r?\n/g, ',')
    .replace(/;/g, ',')
    .split(',')
    .map(chunk => chunk.trim())
    .filter(Boolean)
}

const resolvePublishedHosts = (value: string | undefined): string[] => {
  const candidates = splitCandidates(value)
  const hosts = new Set<string>()

  for (const candidate of candidates) {
    if (candidate.includes('://')) {
      try {
        const url = new URL(candidate)
        if (url.host) {
          hosts.add(url.host)
        }
        continue
      } catch {
        // ignore malformed URL and try parsing below
      }
    }

    const withoutScheme = candidate.replace(/^https?:\/\//, '')
    const host = withoutScheme.split(/[/?#]/)[0]
    if (host) {
      hosts.add(host)
    }
  }

  if (hosts.size === 0) {
    hosts.add(DEFAULT_PUBLISHED_HOST)
  }

  return Array.from(hosts)
}

const [primaryWebAppUrl] = splitCandidates(process.env.WEBAPP_URL)

const resolveAppBasePath = (value: string | undefined): string => {
  if (!value) {
    return '/'
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return '/'
  }

  try {
    const url = new URL(trimmed)
    const pathname = url.pathname.replace(/\/+$/, '')
    return pathname || '/'
  } catch {
    const normalized = trimmed.replace(/^[^/]*(\/|$)/, (_, slash) => (slash ? '/' : ''))
    const cleaned = normalized.replace(/\/+$/, '')
    if (!cleaned) {
      return '/'
    }
    return cleaned.startsWith('/') ? cleaned : `/${cleaned}`
  }
}

const publishedHosts = resolvePublishedHosts(process.env.WEBAPP_URL)
const primaryPublishedHost = publishedHosts[0] || DEFAULT_PUBLISHED_HOST

const appBasePath = resolveAppBasePath(primaryWebAppUrl)

if (!process.env.VITE_APP_BASE_PATH) {
  process.env.VITE_APP_BASE_PATH = appBasePath
}

const extraAllowedHosts = resolvePublishedHosts(
  process.env.DEV_SERVER_ALLOWED_HOSTS,
)

// Если CloudPub выдаст новый временный домен, добавь его в
// DEV_SERVER_ALLOWED_HOSTS — он автоматически попадёт в allowlist.

const allowedHosts = new Set<string | RegExp>([
  /\.caloiq\.ru$/,
  'caloiq.ru',
  ...publishedHosts,
  ...extraAllowedHosts,
])

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_BASE_PATH__: JSON.stringify(appBasePath),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
  server: {
    host: true,            // слушать 0.0.0.0 внутри контейнера
    port: 5173,
    // впускаем *.caloiq.ru и опубликованный хост без поддомена
    allowedHosts: Array.from(allowedHosts),
    // HMR через прокси с TLS
    hmr: {
      protocol: 'wss',
      host: primaryPublishedHost,
      clientPort: 443,
    },
  },
})
