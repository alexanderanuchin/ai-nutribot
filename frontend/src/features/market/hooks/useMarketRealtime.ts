import { useEffect, useRef } from 'react'

import { tokenStore } from '../../../utils/storage'
import type { MarketRealtimeEvent, MarketResource } from '../../../types/market'

const RAW_EVENTS_URL = (import.meta.env as Record<string, string | undefined>).VITE_MARKET_EVENTS_URL
const EVENTS_URL = typeof RAW_EVENTS_URL === 'string' && RAW_EVENTS_URL.trim().length > 0
  ? RAW_EVENTS_URL.trim().replace(/\/$/, '')
  : null

const RESOURCE_TO_GROUP: Record<MarketResource, MarketRealtimeEvent['group']> = {
  recipes: 'market.recipes',
  products: 'market.products',
  stores: 'market.stores',
}

export interface UseMarketRealtimeOptions {
  resource: MarketResource
  onEvent: (event: MarketRealtimeEvent) => void
  enabled?: boolean
}

export function useMarketRealtime({ resource, onEvent, enabled = true }: UseMarketRealtimeOptions): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (!enabled) return undefined
    if (typeof window === 'undefined') return undefined
    const token = tokenStore.access
    if (!token) return undefined
    if (!EVENTS_URL) return undefined

    let es: EventSource | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let closed = false
    let attempts = 0
    let listeners: Array<{ type: string; handler: EventListener }> = []

    const cleanup = () => {
      closed = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (es) {
        es.onopen = null
        es.onerror = null
        listeners.forEach(({ type, handler }) => {
          es?.removeEventListener(type, handler)
        })
        listeners = []
        es.close()
        es = null
      }
    }

      const scheduleReconnect = () => {
        if (closed) return
        if (reconnectTimer) {
          clearTimeout(reconnectTimer)
        }
        const delay = Math.min(1000 * 2 ** attempts, 30000)
        reconnectTimer = setTimeout(connect, delay)
      }

    const connect = () => {
      if (closed) return
      const params = new URLSearchParams({ token, resource })
      const url = `${EVENTS_URL}?${params.toString()}`

      es = new EventSource(url)
      const group = RESOURCE_TO_GROUP[resource]
      listeners = []

      const handlePayload = (data: unknown) => {
        const message = (data ?? {}) as Partial<MarketRealtimeEvent['payload']>
        handlerRef.current({
          group,
          resource,
          payload: {
            fresh_count: typeof message.fresh_count === 'number' ? message.fresh_count : undefined,
            highlight_ids: Array.isArray(message.highlight_ids)
              ? message.highlight_ids.filter(value => typeof value === 'number')
              : undefined,
            generated_at: typeof message.generated_at === 'string' ? message.generated_at : undefined,
          },
        })
      }

      const handleEvent = (event: MessageEvent<string>) => {
        if (!event?.data) {
          handlePayload({})
          return
        }
        try {
          const parsed = JSON.parse(event.data)
          handlePayload(parsed)
        } catch (error) {
          console.warn('market realtime: invalid message', error)
        }
      }

      es.onopen = () => {
        attempts = 0
      }

      es.onerror = () => {
        attempts += 1
        es?.close()
        es = null
        scheduleReconnect()
      }

      const addListener = (type: string, handler: EventListener) => {
        es?.addEventListener(type, handler)
        listeners.push({ type, handler })
      }

      addListener(group, handleEvent)
      addListener('message', handleEvent)
      addListener('market.keepalive', () => {
        if (import.meta.env.DEV) {
          console.debug('market realtime: keepalive received')
        }
      })
    }

    connect()

    return cleanup
  }, [enabled, resource])
}