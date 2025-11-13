// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Минимум, чтобы Vite работал через CloudPub/Caloiq домены, не ломая твою логику.
// PUBLIC_BASE_HOST можно задать в .env (например, adversely-congruent-viper.cloudpub.ru).
const DEFAULT_PUBLISHED_HOST = 'adversely-congruent-viper.cloudpub.ru'

const resolvePublishedHost = (value: string | undefined): string => {
  if (!value) {
    return DEFAULT_PUBLISHED_HOST
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return DEFAULT_PUBLISHED_HOST
  }

  if (trimmed.includes('://')) {
    try {
      const url = new URL(trimmed)
      return url.host || DEFAULT_PUBLISHED_HOST
    } catch {
      return DEFAULT_PUBLISHED_HOST
    }
  }

  return trimmed.replace(/^https?:\/\//, '').replace(/\/+$/, '') || DEFAULT_PUBLISHED_HOST
}

const publishedHost = resolvePublishedHost(process.env.WEBAPP_URL)

const allowedHosts = new Set<string | RegExp>([
  /\.cloudpub\.ru$/,
  /\.caloiq\.ru$/,
  'caloiq.ru',
  publishedHost,
])

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
  server: {
    host: true,            // слушать 0.0.0.0 внутри контейнера
    port: 5173,
    // впускаем *.cloudpub.ru, *.caloiq.ru и опубликованный хост без поддомена
    allowedHosts: Array.from(allowedHosts),
    // HMR через прокси с TLS
    hmr: {
      protocol: 'wss',
      host: publishedHost,
      clientPort: 443,
    },
  },
})
