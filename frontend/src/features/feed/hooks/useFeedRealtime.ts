import { useEffect, useRef } from 'react'

import { tokenStore } from '../../../utils/storage'
import type { FeedRealtimeEvent, FeedTab } from '../../../types/feed'
import { GROUP_TO_TAB } from '../constants'

export interface UseFeedRealtimeOptions {
  feed: FeedTab
  onEvent: (event: FeedRealtimeEvent) => void
}

function resolveHttpBase(): string {
  const base = (import.meta.env.VITE_API_BASE || '/api') as string
  if (base.startsWith('http')) {
    return base.replace(/\/$/, '')
  }
  if (typeof window === 'undefined') return base
  if (base.startsWith('/')) {
    return `${window.location.origin}${base}`.replace(/\/$/, '')
  }
  return `${window.location.origin}/${base}`.replace(/\/$/, '')
}

function resolveWsBase(): string {
  const custom = (import.meta.env as any)?.VITE_WS_BASE as string | undefined
  if (custom && typeof custom === 'string') {
    return custom.replace(/\/$/, '')
  }
  if (typeof window === 'undefined') return 'ws://localhost'
  const { protocol, host } = window.location
  const scheme = protocol === 'https:' ? 'wss:' : 'ws:'
  return `${scheme}//${host}`
}

export function useFeedRealtime({ feed, onEvent }: UseFeedRealtimeOptions): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const token = tokenStore.access
    if (!token) return undefined

    const httpBase = resolveHttpBase()
    const wsBase = resolveWsBase()
    const params = new URLSearchParams({ token, type: 'all' })

    let ws: WebSocket | null = null
    let es: EventSource | null = null
    let sseHandlers: Array<{ type: string; listener: EventListener }> = []
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let closed = false
    let lastKeepAliveAt = Date.now()

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

    const handleEvent = (group: string | undefined, payload: any) => {
      if (!group) return
      const normalizedGroup = group as FeedRealtimeEvent['group']
      const tab = GROUP_TO_TAB[normalizedGroup]
      if (!tab) return
      handlerRef.current({ group: normalizedGroup, tab, payload })
    }

    const connectSse = () => {
      if (closed) return
      const url = `${httpBase}/v1/feed/events/?${params.toString()}`
      es = new EventSource(url)
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

      register('feed.news', createEventHandler('feed.news'))
      register('feed.recipes', createEventHandler('feed.recipes'))
      register('feed.deals', createEventHandler('feed.deals'))
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
          reconnectTimer = setTimeout(connectSse, 5000)
        }
      }
    }

    const connectWebSocket = () => {
      if (closed) return
      const url = `${wsBase}/ws/feed/?${params.toString()}`
      try {
        ws = new WebSocket(url)
      } catch (_error) {
        connectSse()
        return
      }
      ws.onmessage = event => {
        try {
          const data = JSON.parse(event.data) as { type?: string; payload?: unknown; group?: string }
          if (data.type === 'event' && data.payload) {
            handleEvent(data.group, data.payload)
          }
        } catch (error) {
          console.warn('feed realtime: invalid message', error)
        }
      }
      ws.onclose = () => {
        ws = null
        if (!closed) {
          reconnectTimer = setTimeout(connectSse, 1500)
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