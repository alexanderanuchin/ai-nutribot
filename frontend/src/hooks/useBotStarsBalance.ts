import { useQuery } from '@tanstack/react-query'
import { fetchBotStarsBalance, type BotStarsBalance } from '../api/api'

export function useBotStarsBalance(enabled: boolean) {
  return useQuery<BotStarsBalance>({
    queryKey: ['bot-stars-balance'],
    queryFn: fetchBotStarsBalance,
    enabled,
    refetchInterval: enabled ? 60_000 : false,
    staleTime: 30_000,
  })
}

export default useBotStarsBalance