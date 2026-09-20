import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getIncidents } from '../../services/incidents'
import { downloadReportFile, generateReport, getReport, getReports } from '../../services/reports'
import type { Report, ReportFormat } from '../../types'
import { queryKeys } from './queryKeys'

export function useIncidentsForReports() {
  return useQuery({
    queryKey: queryKeys.incidents({}),
    queryFn: () => getIncidents({ limit: 200 }),
  })
}

export function useReportsQuery(params: { incident_id?: string } = {}) {
  return useQuery({
    queryKey: ['reports', 'list', params],
    queryFn: () => getReports({ ...params, limit: 200 }),
  })
}

export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ incidentId, format }: { incidentId: string; format: ReportFormat }) =>
      generateReport(incidentId, format),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', 'list'] })
    },
  })
}

export function useReportQuery(reportId: string | undefined) {
  return useQuery({
    queryKey: ['reports', reportId],
    queryFn: () => getReport(reportId!),
    enabled: !!reportId,
  })
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: (report: Pick<Report, 'id' | 'incident_id' | 'format'>) => downloadReportFile(report),
  })
}
