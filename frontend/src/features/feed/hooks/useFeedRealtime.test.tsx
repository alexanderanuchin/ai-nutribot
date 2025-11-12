import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { FeedRealtimeEvent, FeedTab } from '../../../types/feed'
import { useFeedRealtime } from './useFeedRealtime'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  readyState = MockWebSocket.CONNECTING
  closeCalls = 0
  private listeners = new Map<string, Set<EventListener>>()

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type)!.add(listener)
  }

  removeEventListener(type: string, listener: EventListener): void {
    this.listeners.get(type)?.delete(listener)
  }

  dispatch(type: string, event: Event): void {
    this.listeners.get(type)?.forEach(listener => {
      listener(event)
    })
  }

  open(): void {
    if (this.readyState !== MockWebSocket.CONNECTING) return
    this.readyState = MockWebSocket.OPEN
    const event = new Event('open')
    this.onopen?.(event)
    this.dispatch('open', event)
  }

  send(): void {}

  close(): void {
    this.closeCalls += 1
    if (this.readyState === MockWebSocket.CLOSED) return
    this.readyState = MockWebSocket.CLOSING
    const event = new Event('close')
    this.onclose?.(event as unknown as CloseEvent)
    this.dispatch('close', event)
    this.readyState = MockWebSocket.CLOSED
  }
}

class MockEventSource {
  static instances: MockEventSource[] = []
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  private listeners = new Map<string, Set<EventListener>>()

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type)!.add(listener)
  }

  removeEventListener(type: string, listener: EventListener): void {
    this.listeners.get(type)?.delete(listener)
  }

  dispatch(type: string, payload: unknown): void {
    this.listeners.get(type)?.forEach(listener => {
      listener({ data: JSON.stringify(payload) } as MessageEvent<string>)
    })
  }

  close(): void {}
}

function TestComponent({ feed, onEvent }: { feed: FeedTab; onEvent: (event: FeedRealtimeEvent) => void }) {
  useFeedRealtime({ feed, onEvent })
  return null
}

let localStorageSnapshot: Record<string, string> = {}

beforeEach(() => {
  MockWebSocket.instances = []
  MockEventSource.instances = []
  vi.restoreAllMocks()
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.stubGlobal('EventSource', MockEventSource)
  localStorageSnapshot = {}
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index)
    if (key) {
      localStorageSnapshot[key] = localStorage.getItem(key) ?? ''
    }
  }
  localStorage.setItem('nutribot_access', 'token')
})

afterEach(() => {
  localStorage.clear()
  Object.entries(localStorageSnapshot).forEach(([key, value]) => {
    localStorage.setItem(key, value)
  })
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

describe('useFeedRealtime', () => {
  it('emits events from websocket', async () => {
    const handler = vi.fn()

    render(<TestComponent feed="news" onEvent={handler} />)
    await flushEffects()
    const socket = MockWebSocket.instances[0]
    expect(socket).toBeDefined()

    act(() => {
      socket!.open()
    })

    const payload = {
      type: 'event',
      group: 'feed.news',
      payload: {
        action: 'created',
        article: {
          id: 1,
          source_id: 'ext-1',
          title: 'Новость',
          lead: 'Лид',
          source_name: 'Источник',
          source_url: 'https://example.com',
          published_at: '2024-12-02T08:00:00Z',
          preview_image_url: '',
          tonality: 'neutral',
          source_categories: [],
          toxicity_score: '0.1',
          clickbait_score: '0.2',
          is_flagged: false,
          ingested_at: null,
          ingestion_source: '',
          ingestion_rid: '',
          ingestion_metadata: null,
          created_at: '2024-12-02T08:00:00Z',
          updated_at: '2024-12-02T08:00:00Z',
          tags: [],
        },
        meta: { rid: 'rid-test' },
      },
    }

    act(() => {
      socket!.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent<string>)
    })

    expect(handler).toHaveBeenCalledWith({
      group: 'feed.news',
      tab: 'news',
      payload: expect.objectContaining({ action: 'created' }),
    })
  })

  it('falls back to SSE after repeated websocket failures', async () => {
    vi.useFakeTimers()
    const handler = vi.fn()

    render(<TestComponent feed="news" onEvent={handler} />)
    await flushEffects()
    expect(MockWebSocket.instances).toHaveLength(1)

    act(() => {
      MockWebSocket.instances[0].close()
    })
    await flushEffects()
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()
    expect(MockWebSocket.instances).toHaveLength(2)

    act(() => {
      MockWebSocket.instances[1].close()
    })
    await flushEffects()
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()
    expect(MockWebSocket.instances).toHaveLength(3)

    act(() => {
      MockWebSocket.instances[2].close()
    })
    await flushEffects()
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()

    expect(MockEventSource.instances).toHaveLength(1)
  })

  it('handles SSE named events and message fallback payloads', async () => {
    vi.useFakeTimers()
    const handler = vi.fn()

    render(<TestComponent feed="news" onEvent={handler} />)
    await flushEffects()

    act(() => {
      MockWebSocket.instances[0].close()
    })
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()

    act(() => {
      MockWebSocket.instances[1].close()
    })
    await flushEffects()
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()

    act(() => {
      MockWebSocket.instances[2].close()
    })
    await flushEffects()
    act(() => {
      vi.runOnlyPendingTimers()
    })
    await flushEffects()

    const eventSource = MockEventSource.instances[0]
    expect(eventSource).toBeDefined()

    const newsPayload = {
      action: 'created' as const,
      article: {
        id: 1,
        source_id: 'ext-1',
        title: 'Новость',
        lead: 'Лид',
        source_name: 'Источник',
        source_url: 'https://example.com',
        published_at: '2024-12-02T08:00:00Z',
        preview_image_url: '',
        tonality: 'neutral' as const,
        source_categories: [],
        toxicity_score: '0.1',
        clickbait_score: '0.2',
        is_flagged: false,
        ingested_at: null,
        ingestion_source: '',
        ingestion_rid: '',
        ingestion_metadata: null,
        created_at: '2024-12-02T08:00:00Z',
        updated_at: '2024-12-02T08:00:00Z',
        tags: [],
      },
      meta: { rid: 'rid-test' },
    }

    act(() => {
      eventSource!.dispatch('feed.news', newsPayload)
    })

    expect(handler).toHaveBeenCalledWith({
      group: 'feed.news',
      tab: 'news',
      payload: expect.objectContaining({ action: 'created' }),
    })

    handler.mockClear()

    act(() => {
      eventSource!.dispatch('message', { group: 'feed.recipes', payload: newsPayload })
    })

    expect(handler).toHaveBeenCalledWith({
      group: 'feed.recipes',
      tab: 'recipes',
      payload: expect.objectContaining({ action: 'created' }),
    })
  })

  it('defers closing connecting websocket until handshake completes', async () => {
    const handler = vi.fn()

    const { rerender } = render(<TestComponent feed="news" onEvent={handler} />)
    await flushEffects()
    const socket = MockWebSocket.instances[0]
    expect(socket).toBeDefined()
    expect(socket!.closeCalls).toBe(0)

    rerender(<TestComponent feed="deals" onEvent={handler} />)
    expect(socket!.closeCalls).toBe(0)
    expect(socket!.readyState).toBe(MockWebSocket.CONNECTING)

    act(() => {
      socket!.open()
    })

    expect(socket!.closeCalls).toBe(1)
    expect(socket!.readyState).toBe(MockWebSocket.CLOSED)
  })
})
