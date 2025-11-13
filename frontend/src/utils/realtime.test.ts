import { afterEach, describe, expect, it, vi } from 'vitest'

import { resolveRealtimeHttpBase, resolveRealtimeWsBase } from './realtime'

const stubWindowLocation = (href: string) => {
  const url = new URL(href)
  vi.stubGlobal(
    'window',
    {
      location: {
        origin: url.origin,
        protocol: url.protocol,
        host: url.host,
      },
    } as unknown as Window & typeof globalThis,
  )
}

describe('resolveRealtimeHttpBase', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('returns an absolute API base untouched', () => {
    vi.stubEnv('VITE_API_BASE', 'https://api.example.com/v1/')

    expect(resolveRealtimeHttpBase()).toBe('https://api.example.com/v1')
  })

  it('joins a root-relative base with the current origin', () => {
    vi.stubEnv('VITE_API_BASE', '/api/')
    stubWindowLocation('https://app.example.com/dashboard')

    expect(resolveRealtimeHttpBase()).toBe('https://app.example.com/api')
  })

  it('handles non-prefixed bases by inserting a slash', () => {
    vi.stubEnv('VITE_API_BASE', 'api')
    stubWindowLocation('http://localhost:4173/feed')

    expect(resolveRealtimeHttpBase()).toBe('http://localhost:4173/api')
  })

  it('falls back to the configured base when window is unavailable', () => {
    vi.stubEnv('VITE_API_BASE', '/api/')
    vi.stubGlobal('window', undefined as unknown as Window & typeof globalThis)

    expect(resolveRealtimeHttpBase()).toBe('/api')
  })
})

describe('resolveRealtimeWsBase', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('prefers the custom websocket base when provided', () => {
    vi.stubEnv('VITE_WS_BASE', 'wss://socket.example.com/realtime/')

    expect(resolveRealtimeWsBase()).toBe('wss://socket.example.com/realtime')
  })

  it('falls back to localhost when window is unavailable', () => {
    vi.stubGlobal('window', undefined as unknown as Window & typeof globalThis)

    expect(resolveRealtimeWsBase()).toBe('ws://localhost')
  })

  it('derives a secure scheme when the current page is https', () => {
    stubWindowLocation('https://feed.example.com/news')

    expect(resolveRealtimeWsBase()).toBe('wss://feed.example.com')
  })

  it('derives an insecure scheme when the current page is http', () => {
    stubWindowLocation('http://localhost:4173/feed')

    expect(resolveRealtimeWsBase()).toBe('ws://localhost:4173')
  })
})
