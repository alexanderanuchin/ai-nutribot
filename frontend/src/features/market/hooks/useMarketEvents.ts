import { useEffect, useRef } from 'react'

import type { MarketRealtimeEvent, MarketRealtimePayloadMap, MarketResource } from '../../../types/market'
import { resolveRealtimeHttpBase } from '../../../utils/realtime'
import { ensureFreshAccessToken } from '../../../utils/auth'

const RESOURCE_TO_GROUP: Record<MarketResource, MarketRealtimeEvent['group']> = {
  recipes: 'market.recipes',
  products: 'market.products',
  stores: 'market.stores',
}

const GROUP_TO_RESOURCE: Record<MarketRealtimeEvent['group'], MarketResource> = {
  'market.recipes': 'recipes',
  'market.products': 'products',
  'market.stores': 'stores',
}

const ALL_RESOURCES: MarketResource[] = ['recipes', 'products', 'stores']

const KEEPALIVE_EVENT = 'market.keepalive'

export interface UseMarketEventsOptions {
  resource?: MarketResource
  resources?: MarketResource[]
  onEvent: (event: MarketRealtimeEvent) => void
  enabled?: boolean
}

export function useMarketEvents({
  resource,
  resources,
  onEvent,
  enabled = true,
}: UseMarketEventsOptions): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (!enabled) return undefined
    if (typeof window === 'undefined') return undefined

    let eventSource: EventSource | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let closed = false
    let attempts = 0
    let listeners: Array<{ type: string; handler: EventListener }> = []

    const clearReconnectTimer = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    const detachListeners = () => {
      if (!eventSource) return
      for (const { type, handler } of listeners) {
        eventSource.removeEventListener(type, handler)
      }
      listeners = []
    }

    const closeEventSource = () => {
      if (!eventSource) return
      eventSource.onopen = null
      eventSource.onerror = null
      detachListeners()
      eventSource.close()
      eventSource = null
    }

    const cleanup = () => {
      closed = true
      clearReconnectTimer()
      closeEventSource()
    }

    const normalizedResources = (() => {
      if (Array.isArray(resources) && resources.length > 0) {
        const valid = resources.filter((value): value is MarketResource =>
          value === 'recipes' || value === 'products' || value === 'stores'
        )
        if (valid.length > 0) {
          return Array.from(new Set(valid))
        }
      }
      if (resource) {
        return [resource]
      }
      return ALL_RESOURCES
    })()

    const queryResource = normalizedResources.length === 1 ? normalizedResources[0] : null
    const targetGroups =
      queryResource != null
        ? [RESOURCE_TO_GROUP[queryResource]]
        : normalizedResources.map(item => RESOURCE_TO_GROUP[item])

    const connect = async () => {
      if (closed) return
      const token = await ensureFreshAccessToken()
      if (!token || closed) {
        return
      }
      const httpBase = resolveRealtimeHttpBase()
      const params = new URLSearchParams({ token })
      if (queryResource) {
        params.set('resource', queryResource)
      }
      const url = `${httpBase}/v1/market/events/?${params.toString()}`

      closeEventSource()
      listeners = []
      eventSource = new EventSource(url)

      const buildPayload = <T extends MarketResource>(
        targetResource: T,
        data: unknown,
      ): MarketRealtimePayloadMap[T] => {
        const message = (data ?? {}) as Record<string, unknown>
        const basePayload: MarketRealtimePayloadMap[T] = {
          action: typeof message.action === 'string' ? message.action : undefined,
          fresh_count: typeof message.fresh_count === 'number' ? message.fresh_count : undefined,
          highlight_ids: Array.isArray(message.highlight_ids)
            ? message.highlight_ids.filter(value => typeof value === 'number')
            : undefined,
          generated_at: typeof message.generated_at === 'string' ? message.generated_at : undefined,
          meta:
            message.meta && typeof message.meta === 'object' && !Array.isArray(message.meta)
              ? (message.meta as Record<string, unknown>)
              : undefined,
        } as MarketRealtimePayloadMap[T]

        if (targetResource === 'products' && message.product && typeof message.product === 'object') {
          basePayload.product = message.product as MarketRealtimePayloadMap['products']['product']
        }
        if (targetResource === 'recipes' && message.recipe && typeof message.recipe === 'object') {
          basePayload.recipe = message.recipe as MarketRealtimePayloadMap['recipes']['recipe']
        }
        if (targetResource === 'stores' && message.store && typeof message.store === 'object') {
          basePayload.store = message.store as MarketRealtimePayloadMap['stores']['store']
        }
        return basePayload
      }

      const emitEvent = <T extends MarketResource>(
        targetGroup: MarketRealtimeEvent['group'],
        targetResource: T,
        raw: unknown,
      ) => {
        const payload = buildPayload(targetResource, raw)
        handlerRef.current({
          group: targetGroup,
          resource: targetResource,
          payload,
        })
      }

      const handleEvent = (group: MarketRealtimeEvent['group']) => (event: MessageEvent<string>) => {
        if (!event?.data) {
          emitEvent(group, GROUP_TO_RESOURCE[group], {})
          return
        }
        try {
          const parsed = JSON.parse(event.data)
          emitEvent(group, GROUP_TO_RESOURCE[group], parsed)
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
        closeEventSource()
        scheduleReconnect()
      }

      const addListener = (type: string, handler: EventListener) => {
        eventSource?.addEventListener(type, handler)
        listeners.push({ type, handler })
      }

      targetGroups.forEach(group => {
        addListener(group, handleEvent(group))
      })

      addListener('message', event => {
        const messageEvent = event as MessageEvent<string>
        if (!messageEvent.data) return
        try {
          const parsed = JSON.parse(messageEvent.data) as { group?: string; payload?: unknown }
          const groupName = parsed.group
          if (!groupName || typeof groupName !== 'string') return
          const marketGroup = groupName as MarketRealtimeEvent['group']
          const targetResource = GROUP_TO_RESOURCE[marketGroup]
          if (!targetResource) return
          if (queryResource && targetResource !== queryResource) return
          if (!targetGroups.includes(marketGroup)) return
          const payload = Object.prototype.hasOwnProperty.call(parsed, 'payload')
            ? parsed.payload
            : parsed
          emitEvent(marketGroup, targetResource, payload ?? {})
        } catch (error) {
          console.warn('market events: invalid message payload', error)
        }
      })

      addListener(KEEPALIVE_EVENT, () => {
        if (import.meta.env.DEV) {
          console.debug('market events: keepalive received')
        }
      })
    }

    const scheduleReconnect = () => {
      if (closed) return
      clearReconnectTimer()
      const delay = Math.min(1000 * 2 ** attempts, 30000)
      reconnectTimer = window.setTimeout(() => {
        void connect()
      }, delay)
    }

    void connect()

    return cleanup
  }, [enabled, resource, resources])
}