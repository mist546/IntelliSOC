import { api } from './client'
import type { WebsiteScan } from '../types'

export async function createScan(target_url: string): Promise<WebsiteScan> {
  const { data } = await api.post<WebsiteScan>('/api/scans', { target_url }, { timeout: 120000 })
  return data
}

export async function getScans(params: { skip?: number; limit?: number }): Promise<WebsiteScan[]> {
  const { data } = await api.get<WebsiteScan[]>('/api/scans', { params })
  return data
}

export async function getScan(id: number | string): Promise<WebsiteScan> {
  const { data } = await api.get<WebsiteScan>(`/api/scans/${id}`)
  return data
}
