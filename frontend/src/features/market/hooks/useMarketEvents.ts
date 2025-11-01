import { useEffect, useRef } from 'react'

import type { MarketRealtimeEvent, MarketResource } from '../../../types/market'
import { resolveRealtimeHttpBase } from '../../../utils/realtime'
import { tokenStore } from '../../../utils/storage'

const RESOURCE_TO_GROUP: Record<MarketResource, MarketRealtimeEvent['group']> = {
  recipes: 'market.recipes',
  products: 'market.products',
  stores: 'market.stores',
}

const KEEPALIVE_EVENT = 'market.keepalive'

export interface UseMarketEventsOptions {
  resource: MarketResource
  onEvent: (event: MarketRealtimeEvent) => void
  enabled?: boolean
}

export function useMarketEvents({ resource, onEvent, enabled = true }: UseMarketEventsOptions): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (!enabled) return undefined
    if (typeof window === 'undefined') return undefined
    const token = tokenStore.access
    if (!token) return undefined

    let eventSource: EventSource | null = null
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
      if (eventSource) {
        eventSource.onopen = null
        eventSource.onerror = null
        listeners.forEach(({ type, handler }) => {
          eventSource?.removeEventListener(type, handler)
        })
        listeners = []
        eventSource.close()
        eventSource = null
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
      const httpBase = resolveRealtimeHttpBase()
      const params = new URLSearchParams({ token, resource })
      const url = `${httpBase}/v1/market/events/?${params.toString()}`

      eventSource = new EventSource(url)
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
          console.warn('market events: invalid message payload', error)
        }
      }

      eventSource.onopen = () => {
        attempts = 0
      }

      eventSource.onerror = () => {
        if (closed) return
        attempts += 1
        eventSource?.close()
        eventSource = null
        scheduleReconnect()
      }

      const addListener = (type: string, handler: EventListener) => {
        eventSource?.addEventListener(type, handler)
        listeners.push({ type, handler })
      }

      addListener(group, handleEvent)
      addListener('message', handleEvent)
      addListener(KEEPALIVE_EVENT, () => {
        if (import.meta.env.DEV) {
          console.debug('market events: keepalive received')
        }
      })
    }

    connect()

    return cleanup
  }, [enabled, resource])
}