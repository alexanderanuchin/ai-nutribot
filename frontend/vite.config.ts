// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Минимум, чтобы Vite работал через CloudPub-домен, не ломая твою логику.
// PUBLIC_BASE_HOST можно задать в .env (например, adversely-congruent-viper.cloudpub.ru).
const cloudpubHost = process.env.WEBAPP_URL || 'adversely-congruent-viper.cloudpub.ru'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,            // слушать 0.0.0.0 внутри контейнера
    port: 5173,
    // впускаем *.cloudpub.ru
    allowedHosts: [/\.cloudpub\.ru$/],
    // HMR через прокси с TLS
    hmr: {
      protocol: 'wss',
      host: cloudpubHost,
      clientPort: 443,
    },
  },
})
