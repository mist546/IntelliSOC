import { useQuery } from '@tanstack/react-query'
import { getSystemHealth, getVectorDbStatus } from '../../services/systemHealth'
import { queryKeys } from './queryKeys'

const POLL_INTERVAL_MS = 15000

export function useSystemHealthQuery(live: boolean) {
  return useQuery({
    queryKey: queryKeys.systemHealth,
    queryFn: getSystemHealth,
    refetchInterval: live ? POLL_INTERVAL_MS : false,
  })
}

export function useVectorDbStatusQuery(live: boolean) {
  return useQuery({
    queryKey: queryKeys.vectorDbStatus,
    queryFn: getVectorDbStatus,
    retry: false,
    refetchInterval: live ? POLL_INTERVAL_MS : false,
  })
}
