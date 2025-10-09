import type { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'
import api from './client'
import type {
  WalletSummary,
  WalletTransactionRecord,
  WalletOrderRecord,
  WalletOperationPayload,
} from '../types'
import { getInitData } from '../lib/telegram'

function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`
}

function withTelegramInitData<T = unknown>(config?: AxiosRequestConfig<T>): AxiosRequestConfig<T> | undefined {
  const initData = getInitData()
  if (!initData) return config
  return {
    ...(config ?? {}),
    headers: {
      ...(config?.headers ?? {}),
      'X-Telegram-Init-Data': initData,
    },
  }
}

async function unwrap<T>(request: Promise<AxiosResponse<T>>): Promise<T> {
  try {
    const resp = await request
    return resp.data
  } catch (error) {
    const axiosError = error as AxiosError
    const payload = axiosError.response?.data
    if (payload) {
      console.error('Ошибка Orders API', payload)
      let message: string
      if (typeof payload === 'string') {
        message = payload
      } else if (typeof (payload as any)?.detail === 'string') {
        message = (payload as any).detail
      } else {
        message = 'Ошибка при обращении к Orders API'
      }
      const enriched = new Error(message) as Error & { response?: AxiosResponse; data?: unknown }
      enriched.response = axiosError.response
      enriched.data = payload
      throw enriched
    }
    console.error('Ошибка Orders API', error)
    throw error
  }
}

export async function fetchWalletSummary(): Promise<WalletSummary> {
  return unwrap(api.get('/orders/wallet/summary/', withTelegramInitData()))
}

export async function listWalletTransactions(params?: { currency?: 'stars' | 'calo' }): Promise<WalletTransactionRecord[]> {
  return unwrap(api.get('/orders/wallet/transactions/', withTelegramInitData({ params })))
}

export async function walletTopUp(payload: WalletOperationPayload): Promise<WalletTransactionRecord> {
  const config = withTelegramInitData()
  const headers = { ...(config?.headers ?? {}), 'Idempotency-Key': generateIdempotencyKey() }
  return unwrap(
    api.post('/orders/wallet/transactions/topup/', payload, {
      ...(config ?? {}),
      headers,
    })
  )
}

export async function walletWithdraw(payload: WalletOperationPayload): Promise<WalletTransactionRecord> {
  const config = withTelegramInitData()
  const headers = { ...(config?.headers ?? {}), 'Idempotency-Key': generateIdempotencyKey() }
  return unwrap(
    api.post('/orders/wallet/transactions/withdraw/', payload, {
      ...(config ?? {}),
      headers,
    })
  )
}

export interface OrderPayload {
  title: string
  kind: string
  currency: 'stars' | 'calo'
  amount: number
  description?: string
  pay_with_wallet?: boolean
  reference?: string
  metadata?: Record<string, unknown>
}

export async function listOrders(): Promise<WalletOrderRecord[]> {
  return unwrap(api.get('/orders/wallet/orders/', withTelegramInitData()))
}

export async function createOrder(payload: OrderPayload): Promise<WalletOrderRecord> {
  return unwrap(api.post('/orders/wallet/orders/', payload, withTelegramInitData()))
}

export async function payOrder(
  orderId: number,
  payload?: { description?: string; reference?: string; metadata?: Record<string, unknown> }
): Promise<WalletOrderRecord> {
  return unwrap(api.post(`/orders/wallet/orders/${orderId}/pay/`, payload ?? {}, withTelegramInitData()))
}