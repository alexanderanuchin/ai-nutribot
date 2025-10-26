import { useEffect, useRef } from 'react'

import { tokenStore } from '../../../utils/storage'
import type { FeedRealtimeEvent, FeedTab } from '../../../types/feed'
import { resolveRealtimeHttpBase, resolveRealtimeWsBase } from '../../../utils/realtime'
import { GROUP_TO_TAB } from '../constants'

const FEED_GROUPS: ReadonlyArray<FeedRealtimeEvent['group']> = [
  'feed.news',
  'feed.recipes',
  'feed.deals',
]

function isFeedGroup(value: string | null | undefined): value is FeedRealtimeEvent['group'] {
  if (typeof value !== 'string') return false
  return FEED_GROUPS.includes(value as FeedRealtimeEvent['group'])
}

export interface UseFeedRealtimeOptions {
  feed: FeedTab
  onEvent: (event: FeedRealtimeEvent) => void
}

export function useFeedRealtime({ feed, onEvent }: UseFeedRealtimeOptions): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const token = tokenStore.access
    if (!token) return undefined

    const httpBase = resolveRealtimeHttpBase()
    const wsBase = resolveRealtimeWsBase()
    const params = new URLSearchParams({ token, type: feed })

    let ws: WebSocket | null = null
    let es: EventSource | null = null
    let sseHandlers: Array<{ type: string; listener: EventListener }> = []
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let closed = false
    let lastKeepAliveAt = Date.now()
    let wsFailures = 0
    let sseFailures = 0

    type NewsEvent = Extract<FeedRealtimeEvent, { group: 'feed.news' }>
    type RecipeEvent = Extract<FeedRealtimeEvent, { group: 'feed.recipes' }>
    type DealEvent = Extract<FeedRealtimeEvent, { group: 'feed.deals' }>

    const cleanup = () => {
      closed = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (ws) {
        ws.onopen = null
        ws.onmessage = null
        ws.onerror = null
        ws.onclose = null
        ws.close()
        ws = null
      }
      if (es) {
        es.onopen = null
        es.onerror = null
        for (const { type, listener } of sseHandlers) {
          es.removeEventListener(type, listener)
        }
        sseHandlers = []
        es.close()
        es = null
      }
    }

    const scheduleReconnect = (transport: 'ws' | 'sse') => {
      if (closed) return
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      const attempt = transport === 'ws' ? wsFailures : sseFailures
      const delay = Math.min(1000 * 2 ** attempt, 30000)
      reconnectTimer = window.setTimeout(() => {
        if (transport === 'ws') {
          connectWebSocket()
        } else {
          connectSse()
        }
      }, delay)
    }

    const handleEvent = (group: FeedRealtimeEvent['group'], payload: unknown) => {
      const tab = GROUP_TO_TAB[group]
      if (!tab) return
      if (group === 'feed.news') {
        handlerRef.current({
          group,
          tab,
          payload: (payload ?? {}) as NewsEvent['payload'],
        })
        return
      }
      if (group === 'feed.recipes') {
        handlerRef.current({
          group,
          tab,
          payload: (payload ?? {}) as RecipeEvent['payload'],
        })
        return
      }
      handlerRef.current({
        group,
        tab,
        payload: (payload ?? {}) as DealEvent['payload'],
      })
    }

    const connectSse = () => {
      if (closed) return
      const url = `${httpBase}/v1/feed/events/?${params.toString()}`
      es = new EventSource(url)
      es.onopen = () => {
        sseFailures = 0
      }
      const register = (type: string, listener: EventListener) => {
        if (!es) return
        es.addEventListener(type, listener)
        sseHandlers.push({ type, listener })
      }

      const createEventHandler = (group: FeedRealtimeEvent['group']): EventListener => event => {
        const messageEvent = event as MessageEvent<string>
        try {
          const data = messageEvent.data ? JSON.parse(messageEvent.data) : {}
          handleEvent(group, data)
        } catch (error) {
          console.warn('feed realtime: invalid sse message', error)
        }
      }

      for (const group of FEED_GROUPS) {
        register(group, createEventHandler(group))
      }
      register('message', event => {
        const messageEvent = event as MessageEvent<string>
        try {
          const data = messageEvent.data ? JSON.parse(messageEvent.data) : {}
          const group = (data as { group?: string }).group
          if (isFeedGroup(group ?? null)) {
            handleEvent(group, (data as { payload?: unknown }).payload ?? {})
          }
        } catch (error) {
          console.warn('feed realtime: invalid sse message', error)
        }
      })
      register('feed.keepalive', event => {
        const previousKeepAliveAt = lastKeepAliveAt
        lastKeepAliveAt = Date.now()
        if (import.meta.env.DEV) {
          const keepAliveEvent = event as MessageEvent<string>
          try {
            const data = keepAliveEvent.data ? JSON.parse(keepAliveEvent.data) : {}
            console.debug('feed realtime: keepalive', { ...data, sinceLast: lastKeepAliveAt - previousKeepAliveAt })
          } catch (_error) {
            console.debug('feed realtime: keepalive', { sinceLast: lastKeepAliveAt - previousKeepAliveAt })
          }
        }
      })
      es.onerror = () => {
        if (es) {
          for (const { type, listener } of sseHandlers) {
            es.removeEventListener(type, listener)
          }
          es.close()
        }
        es = null
        sseHandlers = []
        if (!closed) {
          sseFailures += 1
          if (sseFailures >= 4) {
            wsFailures = 0
            scheduleReconnect('ws')
          } else {
            scheduleReconnect('sse')
          }
        }
      }
    }

    const connectWebSocket = () => {
      if (closed) return
      const url = `${wsBase}/ws/feed/?${params.toString()}`
      try {
        ws = new WebSocket(url)
      } catch (_error) {
        wsFailures += 1
        sseFailures = 0
        connectSse()
        return
      }
      ws.onopen = () => {
        wsFailures = 0
      }
      ws.onmessage = event => {
        try {
          const data = JSON.parse(event.data) as { type?: string; payload?: unknown; group?: string }
          if (data.type === 'event' && data.payload && data.group) {
            const group = data.group as FeedRealtimeEvent['group']
            if (FEED_GROUPS.includes(group)) {
              handleEvent(group, data.payload)
            }
          }
        } catch (error) {
          console.warn('feed realtime: invalid message', error)
        }
      }
      ws.onclose = () => {
        ws = null
        if (!closed) {
          wsFailures += 1
          if (wsFailures >= 3) {
            sseFailures = 0
            connectSse()
          } else {
            scheduleReconnect('ws')
          }
        }
      }
      ws.onerror = () => {
        ws?.close()
      }
    }

    connectWebSocket()

    return cleanup
  }, [feed])
}