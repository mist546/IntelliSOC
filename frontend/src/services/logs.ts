import { api } from './client'
import type { LogEvent, LogUploadResult } from '../types'

export async function uploadLogFile(file: File): Promise<LogUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<LogUploadResult>('/api/logs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

export async function getLogs(params: {
  skip?: number
  limit?: number
  source_ip?: string
  event_type?: string
  source_type?: string
  wazuh?: boolean
}): Promise<LogEvent[]> {
  const { data } = await api.get<LogEvent[]>('/api/logs', { params })
  return data
}

export async function getLog(id: number | string): Promise<LogEvent> {
  const { data } = await api.get<LogEvent>(`/api/logs/${id}`)
  return data
}
