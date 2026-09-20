import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAlert, getAlerts, investigateAlert, updateAlertStatus } from '../../services/alerts'
import type { Alert, AlertStatus } from '../../types'
import { queryKeys } from './queryKeys'

const POLL_INTERVAL_MS = 15000

export function useAlertsQuery(
  filters: { severity?: string; status?: string; source_ip?: string },
  live: boolean,
) {
  return useQuery({
    queryKey: queryKeys.alerts(filters),
    queryFn: () => getAlerts({ ...filters, limit: 200 }),
    refetchInterval: live ? POLL_INTERVAL_MS : false,
  })
}

export function useRecentAlertsQuery(live: boolean, limit = 8) {
  return useQuery({
    queryKey: ['alerts', 'recent', limit],
    queryFn: () => getAlerts({ limit }),
    refetchInterval: live ? POLL_INTERVAL_MS : false,
  })
}

export function useAlertQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.alert(id ?? ''),
    queryFn: () => getAlert(id!),
    enabled: !!id,
  })
}

export function useUpdateAlertStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: AlertStatus }) => updateAlertStatus(id, status),
    onSuccess: (updated: Alert) => {
      queryClient.setQueryData(queryKeys.alert(updated.id), updated)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useInvestigateAlert() {
  return useMutation({
    mutationFn: (id: string) => investigateAlert(id),
  })
}
