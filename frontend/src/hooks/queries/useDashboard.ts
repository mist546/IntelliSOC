import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '../../services/dashboard'
import { queryKeys } from './queryKeys'

const POLL_INTERVAL_MS = 20000

export function useDashboardStats(live: boolean) {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: getDashboardStats,
    refetchInterval: live ? POLL_INTERVAL_MS : false,
  })
}
