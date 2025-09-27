import api from './client'
import type {
  WalletSummary,
  WalletTransactionRecord,
  WalletOrderRecord,
  WalletOperationPayload,
} from '../types'

export async function fetchWalletSummary(): Promise<WalletSummary> {
  const resp = await api.get('/orders/wallet/summary/')
  return resp.data
}

export async function listWalletTransactions(params?: { currency?: 'stars' | 'calo' }): Promise<WalletTransactionRecord[]> {
  const resp = await api.get('/orders/wallet/transactions/', { params })
  return resp.data
}

export async function walletTopUp(payload: WalletOperationPayload): Promise<WalletTransactionRecord> {
  const resp = await api.post('/orders/wallet/transactions/topup/', payload)
  return resp.data
}

export async function walletWithdraw(payload: WalletOperationPayload): Promise<WalletTransactionRecord> {
  const resp = await api.post('/orders/wallet/transactions/withdraw/', payload)
  return resp.data
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
  const resp = await api.get('/orders/wallet/orders/')
  return resp.data
}

export async function createOrder(payload: OrderPayload): Promise<WalletOrderRecord> {
  const resp = await api.post('/orders/wallet/orders/', payload)
  return resp.data
}

export async function payOrder(
  orderId: number,
  payload?: { description?: string; reference?: string; metadata?: Record<string, unknown> }
): Promise<WalletOrderRecord> {
  const resp = await api.post(`/orders/wallet/orders/${orderId}/pay/`, payload ?? {})
  return resp.data
}