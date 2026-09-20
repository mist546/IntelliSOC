import { api } from './client'
import type { Incident, IncidentDetail } from '../types'

export async function getIncidents(params: { status?: string; skip?: number; limit?: number }): Promise<Incident[]> {
  const { data } = await api.get<Incident[]>('/api/incidents', { params })
  return data
}

export async function getIncident(id: number | string): Promise<IncidentDetail> {
  const { data } = await api.get<IncidentDetail>(`/api/incidents/${id}`)
  return data
}
