/// <reference types="vite/client" />

declare const __APP_BASE_PATH__: string

interface ImportMetaEnv {
  readonly VITE_APP_BASE_PATH?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
