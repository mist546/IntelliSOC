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

export async function investigateAlert(id: number | string): Promise<Investigation> {
  // Must exceed the backend's own worst-case budget: OLLAMA_TIMEOUT (default
  // 240s) plus RAG/threat-intel overhead. A shorter client timeout would
  // abort the UI request while the backend investigation keeps running and
  // completes successfully, showing the user a false failure.
  const { data } = await api.post<Investigation>(
    `/api/alerts/${id}/investigate`,
    {},
    { timeout: 300000 },
  )
  return data
}
