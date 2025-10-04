import { useQuery } from '@tanstack/react-query'
import { fetchWallet } from '../api/api'

export function useWallet() {
  return useQuery({
    queryKey: ['wallet'],
    queryFn: fetchWallet,
    refetchInterval: 1000 * 60 * 5,
    staleTime: 1000 * 60,
  })
}