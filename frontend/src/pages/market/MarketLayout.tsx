import { Outlet } from 'react-router-dom'

import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'
import { useSafeArea } from '../../hooks/useSafeArea'
import MarketSectionNav from '../../features/market/components/MarketSectionNav'

export function MarketLayout() {
  useBodyScrollLock(true)
  const safeArea = useSafeArea({ inset: 16, edges: ['top', 'bottom'] })

  return (
    <div
      className="relative -mx-4 -mt-6 flex min-h-[min(100dvh,calc(100vh-3.5rem))] flex-col overflow-hidden rounded-3xl border border-border/60 bg-background/95 shadow-2xl sm:-mx-6 lg:-mx-10"
      style={{ ...safeArea, overscrollBehavior: 'contain' }}
    >
      <div className="flex flex-col gap-4 border-b border-border/60 bg-background/95/90 px-4 pb-4 pt-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-lg font-semibold uppercase tracking-[0.3em] text-muted-foreground">Маркет</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Заказывайте полезные блюда, продукты и подписки, которые подстраиваются под ваш план NutriBot.
          </p>
        </div>
        <MarketSectionNav />
      </div>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto px-4 pb-[calc(env(safe-area-inset-bottom,0px)+2.5rem)] pt-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

export default MarketLayout