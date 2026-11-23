import { api } from './client'
import type { Alert, AlertStatus, Investigation } from '../types'

export async function getAlerts(params: {
  severity?: string
  status?: string
  source_ip?: string
  skip?: number
  limit?: number
}): Promise<Alert[]> {
  const { data } = await api.get<Alert[]>('/api/alerts', { params })
  return data
}

export async function getAlert(id: number | string): Promise<Alert> {
  const { data } = await api.get<Alert>(`/api/alerts/${id}`)
  return data
}

export async function updateAlertStatus(id: number | string, status: AlertStatus): Promise<Alert> {
  const { data } = await api.patch<Alert>(`/api/alerts/${id}/status`, { status })
  return data
}

/** Starts an AI investigation. The backend answers immediately with the
 * investigation in status RUNNING and keeps working in the background. */
export async function investigateAlert(id: number | string): Promise<Investigation> {
  const { data } = await api.post<Investigation>(`/api/alerts/${id}/investigate`, {})
  return data
}
