import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangleIcon, InfoIcon } from 'lucide-react'

import { TelegramHeroCard } from '../../components/integrations/TelegramHeroCard'
import { TelegramHowItWorks } from '../../components/integrations/TelegramHowItWorks'
import { TelegramStatusCard } from '../../components/integrations/TelegramStatusCard'
import { TelegramChatShell } from '../../components/integrations/TelegramChatShell'
import { Skeleton, useToast } from '../../components/ui'
import { buildStartAppLink } from '../../lib/deeplinks'
import { fetchTelegramStatus, startTelegramLink, type TelegramLinkResponse } from '../../api/telegram'
import { getInitData, isTgWebAppPresent, isTgWebAppRuntime, openTelegramLink, runAuthBridge } from '../../lib/telegram'

export default function TelegramIntegrationPage() {
  const statusQuery = useQuery({ queryKey: ['telegram-status'], queryFn: fetchTelegramStatus })
  const startLinkMutation = useMutation({ mutationFn: startTelegramLink })
  const { notify } = useToast()

  const startAppTarget = (link?: TelegramLinkResponse | null) =>
    link?.links?.startapp || buildStartAppLink(link?.code || 'dashboard')

  const buildDiag = useMemo(
    () =>
      function computeDiag() {
        const present = isTgWebAppPresent()
        const runtime = isTgWebAppRuntime()
        const initData = typeof window !== 'undefined' ? getInitData() : null
        return {
          present,
          initDataLength: initData?.length || 0,
          initDataPreview: initData ? initData.slice(0, 16) : '',
          runtime,
          mainButtonAvailable: present && Boolean((window as any)?.Telegram?.WebApp?.MainButton),
        }
      },
    [],
  )

  const [diag, setDiag] = useState(buildDiag)

  useEffect(() => {
    const refresh = () => setDiag(buildDiag())
    refresh()
    const id = window.setInterval(refresh, 4000)
    return () => window.clearInterval(id)
  }, [buildDiag])

  const isLoading = statusQuery.isLoading && !statusQuery.data

  const ensureLink = async (): Promise<TelegramLinkResponse | undefined> => {
    try {
      if (statusQuery.data?.link) return statusQuery.data.link
      const link = await startLinkMutation.mutateAsync()
      void statusQuery.refetch()
      return link
    } catch (error) {
      notify({
        title: 'Не удалось создать ссылку',
        description: error instanceof Error ? error.message : 'Попробуйте ещё раз из Telegram',
        tone: 'warning',
      })
      throw error
    }
  }

  const handleOpenMiniApp = async () => {
    try {
      const link = await ensureLink()
      const target = startAppTarget(link || statusQuery.data?.link)
      if (target) {
        openTelegramLink(target)
      }
    } finally {
      setDiag(buildDiag())
    }
  }

  const handleOpenTelegramLogin = async () => {
    try {
      const link = await ensureLink()
      const payload = link?.code || statusQuery.data?.link?.code || 'dashboard'
      await runAuthBridge(payload)
    } finally {
      setDiag(buildDiag())
    }
  }

  return (
    <div className="space-y-6">
      {isLoading ? (
        <TelegramHeroSkeleton />
      ) : (
          <TelegramHeroCard
            startLink={statusQuery.data?.link?.links?.tme}
            startAppLink={startAppTarget(statusQuery.data?.link)}
            onOpenMiniApp={handleOpenMiniApp}
            onOpenTelegram={handleOpenTelegramLogin}
            loading={statusQuery.isLoading || startLinkMutation.isPending}
          />
      )}

      <div className="grid gap-4 lg:grid-cols-[2fr,1.2fr]">
        <div className="space-y-4">
          <TelegramHowItWorks />
          <TelegramChatShell
            startAppLink={startAppTarget(statusQuery.data?.link)}
            linked={Boolean(statusQuery.data?.linked)}
          />
        </div>
        <div className="space-y-4">
          {isLoading ? (
            <TelegramStatusSkeleton />
          ) : (
            <TelegramStatusCard
              status={statusQuery.data}
              onCreateLink={() =>
                startLinkMutation.mutate(void 0, {
                  onSuccess: () => statusQuery.refetch(),
                  onError: error =>
                    notify({
                      title: 'Не удалось обновить ссылку',
                      description: error instanceof Error ? error.message : undefined,
                      tone: 'warning',
                    }),
                })
              }
              loading={startLinkMutation.isPending}
            />
          )}
          <div className="rounded-2xl border border-border/60 bg-card p-4 text-sm text-muted-foreground shadow-level-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <InfoIcon className="h-4 w-4" aria-hidden="true" /> Диагностика окружения
            </div>
            <div className="mt-2 space-y-1 text-xs">
              <div>tgPresent: {String(diag.present)}</div>
              <div>initData length: {diag.initDataLength}</div>
              <div>initData preview: {diag.initDataPreview}</div>
              <div>webapp runtime: {String(diag.runtime)}</div>
              <div>MainButton: {String(diag.mainButtonAvailable)}</div>
            </div>
            {!diag.present && (
              <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-100">
                <AlertTriangleIcon className="mt-0.5 h-4 w-4" aria-hidden="true" />
                Откройте Mini App из inline‑кнопки в Telegram, чтобы передать initData. В браузере Mini App не инициализируется.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function TelegramHeroSkeleton() {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-sky-600/15 via-indigo-600/10 to-slate-900/10 p-6 ring-1 ring-border shadow-2xl">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex flex-col gap-3 md:max-w-[60%]">
          <Skeleton className="h-7 w-40 bg-white/30" shimmer={false} />
          <Skeleton className="h-10 w-full max-w-md bg-white/40" shimmer={false} />
          <Skeleton className="h-12 w-full max-w-2xl bg-white/20" shimmer />
          <div className="flex flex-wrap items-center gap-3">
            <Skeleton className="h-12 w-56 bg-white/30" />
            <Skeleton className="h-12 w-48 bg-white/20" />
          </div>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-white/10 p-4 shadow-inner backdrop-blur">
          <Skeleton className="h-6 w-40 bg-white/30" shimmer={false} />
          <Skeleton className="h-40 w-40 rounded-xl bg-white/40" />
          <Skeleton className="h-5 w-48 bg-white/20" />
        </div>
      </div>
    </div>
  )
}

function TelegramStatusSkeleton() {
  return (
    <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-level-1">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-9 w-36" />
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  )
}
