import { api, getApiBaseUrl } from './client'
import type { Report, ReportFormat } from '../types'

export async function generateReport(incidentId: number | string, format: ReportFormat): Promise<Report> {
  const { data } = await api.post<Report>(`/api/reports/${incidentId}`, { format })
  return data
}

export async function getReport(reportId: number | string): Promise<Report> {
  const { data } = await api.get<Report>(`/api/reports/${reportId}`)
  return data
}

export async function getReports(params: { incident_id?: string; skip?: number; limit?: number } = {}): Promise<Report[]> {
  const { data } = await api.get<Report[]>('/api/reports', { params })
  return data
}

export function getReportDownloadUrl(reportId: number | string): string {
  return `${getApiBaseUrl()}/api/reports/${reportId}/download`
}

// The download endpoint requires the same Authorization header as every
// other API call, so a plain <a href=...> anchor can't be used - the browser
// won't attach it to a raw navigation. Fetch the file as a blob through the
// authenticated axios instance instead, then trigger a client-side save.
export async function downloadReportFile(report: Pick<Report, 'id' | 'incident_id' | 'format'>): Promise<void> {
  const response = await api.get(`/api/reports/${report.id}/download`, { responseType: 'blob' })
  const extension = report.format === 'pdf' ? 'pdf' : 'json'
  const filename = `incident_report_${report.incident_id}.${extension}`
  const url = URL.createObjectURL(response.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
