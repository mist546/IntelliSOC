import { api } from './client'
import type { Investigation, InvestigationSummary, InvestigationTraceResponse } from '../types'

export async function getInvestigations(params: { status?: string; skip?: number; limit?: number }): Promise<InvestigationSummary[]> {
  const { data } = await api.get<InvestigationSummary[]>('/api/investigations', { params })
  return data
}

export async function getInvestigation(id: number | string): Promise<Investigation> {
  const { data } = await api.get<Investigation>(`/api/investigations/${id}`)
  return data
}

export async function getInvestigationTrace(id: number | string): Promise<InvestigationTraceResponse> {
  const { data } = await api.get<InvestigationTraceResponse>(`/api/investigations/${id}/trace`)
  return data
}
