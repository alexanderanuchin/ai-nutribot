import React, { useCallback, useEffect, useState } from 'react'
import {
  fetchWalletSummary,
  listWalletTransactions,
  walletTopUp,
  walletWithdraw,
  listOrders,
  createOrder,
  payOrder,
} from '../api/orders'
import type {
  WalletCurrency,
  WalletOrderRecord,
  WalletSummary,
  WalletTransactionRecord,
} from '../types'

interface OperationFormState {
  currency: WalletCurrency
  amount: string
  description: string
}

interface OrderFormState {
  title: string
  amount: string
  currency: WalletCurrency
  pay_with_wallet: boolean
  description: string
}

const currencyLabels: Record<WalletCurrency, string> = {
  stars: 'Telegram Stars',
  calo: 'CaloCoin',
}

const numberFormatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

export default function Orders(): JSX.Element {
  const [summary, setSummary] = useState<WalletSummary | null>(null)
  const [transactions, setTransactions] = useState<WalletTransactionRecord[]>([])
  const [orders, setOrders] = useState<WalletOrderRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [topupForm, setTopupForm] = useState<OperationFormState>({ currency: 'stars', amount: '150', description: '' })
  const [withdrawForm, setWithdrawForm] = useState<OperationFormState>({ currency: 'calo', amount: '100', description: '' })
  const [orderForm, setOrderForm] = useState<OrderFormState>({
    title: 'PRO подписка',
    amount: '500',
    currency: 'calo',
    pay_with_wallet: true,
    description: 'Подписка на PRO-доступ',
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, txData, ordersData] = await Promise.all([
        fetchWalletSummary(),
        listWalletTransactions(),
        listOrders(),
      ])
      setSummary(summaryData)
      setTransactions(txData)
      setOrders(ordersData)
    } catch (err) {
      console.error('Не удалось загрузить данные монетизации', err)
      setError('Не удалось загрузить данные монетизации. Попробуйте обновить страницу.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(() => setMessage(null), 5000)
    return () => window.clearTimeout(timer)
  }, [message])

  const parseAmount = (value: string): number | null => {
    if (!value) return null
    const parsed = Number(value.replace(',', '.'))
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null
  }

  const handleTopUpSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const amount = parseAmount(topupForm.amount)
    if (amount === null) {
      setError('Введите корректную сумму для пополнения')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await walletTopUp({
        currency: topupForm.currency,
        amount,
        description: topupForm.description.trim() || undefined,
      })
      setMessage('Баланс успешно пополнен')
      setTopupForm(prev => ({ ...prev, description: '' }))
      await loadData()
    } catch (err) {
      console.error('Ошибка пополнения', err)
      setError('Не удалось пополнить баланс. Проверьте данные и повторите попытку.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleWithdrawSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const amount = parseAmount(withdrawForm.amount)
    if (amount === null) {
      setError('Введите корректную сумму для списания')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await walletWithdraw({
        currency: withdrawForm.currency,
        amount,
        description: withdrawForm.description.trim() || undefined,
      })
      setMessage('Списание выполнено')
      setWithdrawForm(prev => ({ ...prev, description: '' }))
      await loadData()
    } catch (err: any) {
      console.error('Ошибка списания', err)
      const detail = err?.response?.data?.amount || err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Не удалось списать средства. Проверьте баланс.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleOrderSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const amount = parseAmount(orderForm.amount)
    if (amount === null) {
      setError('Введите корректную сумму заказа')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await createOrder({
        title: orderForm.title.trim() || 'Заказ',
        currency: orderForm.currency,
        amount,
        description: orderForm.description.trim() || undefined,
        pay_with_wallet: orderForm.pay_with_wallet,
      })
      setMessage(orderForm.pay_with_wallet ? 'Заказ создан и оплачен из кошелька' : 'Заказ создан')
      await loadData()
    } catch (err: any) {
      console.error('Ошибка создания заказа', err)
      const detail = err?.response?.data?.pay_with_wallet || err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Не удалось создать заказ. Попробуйте ещё раз.')
    } finally {
      setSubmitting(false)
    }
  }

  const handlePayOrder = async (orderId: number) => {
    setSubmitting(true)
    setError(null)
    try {
      await payOrder(orderId)
      setMessage('Заказ оплачен из кошелька')
      await loadData()
    } catch (err: any) {
      console.error('Ошибка оплаты заказа', err)
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Не удалось оплатить заказ из кошелька.')
    } finally {
      setSubmitting(false)
    }
  }

  const recentTransactions = transactions.slice(0, 8)

  return (
    <div className="orders-page">
      <div className="card orders-summary">
        <h1 className="orders-title">Монетизация и заказы</h1>
        <p className="orders-subtitle">
          Управляйте балансами Stars и CaloCoin, фиксируйте реальные транзакции и мгновенно оплачивайте заказы из кошелька.
        </p>
        {error && <div className="orders-alert orders-alert--error">{error}</div>}
        {message && <div className="orders-alert orders-alert--success">{message}</div>}
        {loading ? (
          <div className="orders-loading">Загружаем баланс и историю...</div>
        ) : summary ? (
          <div className="orders-targets">
            <div className="orders-target">
              <div className="orders-target-label">Telegram Stars</div>
              <div className="orders-target-value">{numberFormatter.format(summary.targets.stars.balance)}</div>
              <div className="orders-target-progress">
                <div className="orders-target-progress-bar" aria-hidden="true">
                  <span style={{ width: `${summary.targets.stars.progress}%` }} />
                </div>
                <div className="orders-target-hint">
                  {summary.targets.stars.left > 0
                    ? `Ещё ${numberFormatter.format(summary.targets.stars.left)} Stars до клубной консультации`
                    : 'Цель достигнута — доступ к консультациям открыт'}
                </div>
              </div>
            </div>
            <div className="orders-target">
              <div className="orders-target-label">CaloCoin</div>
              <div className="orders-target-value">{numberFormatter.format(summary.targets.calo.balance)}</div>
              <div className="orders-target-progress">
                <div className="orders-target-progress-bar" aria-hidden="true">
                  <span style={{ width: `${summary.targets.calo.progress}%` }} />
                </div>
                <div className="orders-target-hint">
                  {summary.targets.calo.left > 0
                    ? `Нужно ещё ${numberFormatter.format(summary.targets.calo.left)} CaloCoin для PRO-доступа`
                    : 'Баланс готов к активации PRO прямо сейчас'}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="orders-loading">Нет данных по кошельку</div>
        )}
      </div>

      <div className="orders-grid">
        <section className="card orders-operations">
          <h2>Операции с кошельком</h2>
          <form className="orders-form" onSubmit={handleTopUpSubmit}>
            <h3>Пополнить баланс</h3>
            <label className="orders-field">
              <span>Валюта</span>
              <select
                value={topupForm.currency}
                onChange={event => setTopupForm(prev => ({ ...prev, currency: event.target.value as WalletCurrency }))}
                disabled={submitting}
              >
                <option value="stars">Telegram Stars</option>
                <option value="calo">CaloCoin</option>
              </select>
            </label>
            <label className="orders-field">
              <span>Сумма</span>
              <input
                type="number"
                min="1"
                step="0.01"
                value={topupForm.amount}
                onChange={event => setTopupForm(prev => ({ ...prev, amount: event.target.value }))}
                disabled={submitting}
                required
              />
            </label>
            <label className="orders-field">
              <span>Комментарий (необязательно)</span>
              <input
                type="text"
                value={topupForm.description}
                onChange={event => setTopupForm(prev => ({ ...prev, description: event.target.value }))}
                disabled={submitting}
              />
            </label>
            <button type="submit" className="orders-button" disabled={submitting}>
              Пополнить
            </button>
          </form>

          <form className="orders-form" onSubmit={handleWithdrawSubmit}>
            <h3>Списать средства</h3>
            <label className="orders-field">
              <span>Валюта</span>
              <select
                value={withdrawForm.currency}
                onChange={event => setWithdrawForm(prev => ({ ...prev, currency: event.target.value as WalletCurrency }))}
                disabled={submitting}
              >
                <option value="stars">Telegram Stars</option>
                <option value="calo">CaloCoin</option>
              </select>
            </label>
            <label className="orders-field">
              <span>Сумма</span>
              <input
                type="number"
                min="1"
                step="0.01"
                value={withdrawForm.amount}
                onChange={event => setWithdrawForm(prev => ({ ...prev, amount: event.target.value }))}
                disabled={submitting}
                required
              />
            </label>
            <label className="orders-field">
              <span>Комментарий (необязательно)</span>
              <input
                type="text"
                value={withdrawForm.description}
                onChange={event => setWithdrawForm(prev => ({ ...prev, description: event.target.value }))}
                disabled={submitting}
              />
            </label>
            <button type="submit" className="orders-button orders-button--secondary" disabled={submitting}>
              Списать
            </button>
          </form>

          <form className="orders-form" onSubmit={handleOrderSubmit}>
            <h3>Создать заказ</h3>
            <label className="orders-field">
              <span>Название</span>
              <input
                type="text"
                value={orderForm.title}
                onChange={event => setOrderForm(prev => ({ ...prev, title: event.target.value }))}
                disabled={submitting}
                required
              />
            </label>
            <label className="orders-field">
              <span>Сумма</span>
              <input
                type="number"
                min="1"
                step="0.01"
                value={orderForm.amount}
                onChange={event => setOrderForm(prev => ({ ...prev, amount: event.target.value }))}
                disabled={submitting}
                required
              />
            </label>
            <label className="orders-field">
              <span>Валюта</span>
              <select
                value={orderForm.currency}
                onChange={event => setOrderForm(prev => ({ ...prev, currency: event.target.value as WalletCurrency }))}
                disabled={submitting}
              >
                <option value="stars">Telegram Stars</option>
                <option value="calo">CaloCoin</option>
              </select>
            </label>
            <label className="orders-checkbox">
              <input
                type="checkbox"
                checked={orderForm.pay_with_wallet}
                onChange={event => setOrderForm(prev => ({ ...prev, pay_with_wallet: event.target.checked }))}
                disabled={submitting}
              />
              <span>Сразу оплатить из кошелька</span>
            </label>
            <label className="orders-field">
              <span>Комментарий (необязательно)</span>
              <input
                type="text"
                value={orderForm.description}
                onChange={event => setOrderForm(prev => ({ ...prev, description: event.target.value }))}
                disabled={submitting}
              />
            </label>
            <button type="submit" className="orders-button orders-button--accent" disabled={submitting}>
              Создать заказ
            </button>
          </form>
        </section>

        <section className="card orders-history">
          <h2>История транзакций</h2>
          {recentTransactions.length === 0 ? (
            <p className="orders-empty">Пока нет операций по кошельку.</p>
          ) : (
            <ul className="orders-transaction-list">
              {recentTransactions.map(tx => {
                const created = new Date(tx.created_at)
                const dateDisplay = Number.isNaN(created.getTime()) ? '' : created.toLocaleString('ru-RU')
                const amountDisplay = `${tx.direction === 'in' ? '+' : '−'} ${numberFormatter.format(Math.abs(tx.amount))} ${currencyLabels[tx.currency]}`
                return (
                  <li key={tx.id} className={`orders-transaction orders-transaction--${tx.direction === 'in' ? 'credit' : 'debit'}`}>
                    <div>
                      <div className="orders-transaction-title">{tx.description || (tx.direction === 'in' ? 'Пополнение' : 'Списание')}</div>
                      <div className="orders-transaction-meta">{dateDisplay}</div>
                    </div>
                    <div className="orders-transaction-amount">{amountDisplay}</div>
                  </li>
                )
              })}
            </ul>
          )}

          <h2>Заказы</h2>
          {orders.length === 0 ? (
            <p className="orders-empty">Создайте заказ, чтобы активировать реальный сценарий монетизации.</p>
          ) : (
            <ul className="orders-order-list">
              {orders.map(order => {
                const created = new Date(order.created_at)
                const dateDisplay = Number.isNaN(created.getTime()) ? '' : created.toLocaleString('ru-RU')
                const amountDisplay = `${numberFormatter.format(order.amount)} ${currencyLabels[order.currency]}`
                const canPay = order.status !== 'paid'
                return (
                  <li key={order.id} className="orders-order">
                    <div className="orders-order-main">
                      <div className="orders-order-title">{order.title}</div>
                      <div className="orders-order-meta">
                        {amountDisplay} · {order.status_display}
                        {dateDisplay ? ` · ${dateDisplay}` : ''}
                      </div>
                    </div>
                    {canPay && (
                      <button
                        type="button"
                        className="orders-button orders-button--ghost"
                        onClick={() => handlePayOrder(order.id)}
                        disabled={submitting}
                      >
                        Оплатить из кошелька
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}