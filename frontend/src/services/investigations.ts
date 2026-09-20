import { api } from './client'
import type { Investigation, InvestigationTraceResponse } from '../types'

export async function getInvestigation(id: number | string): Promise<Investigation> {
  const { data } = await api.get<Investigation>(`/api/investigations/${id}`)
  return data
}

export async function getInvestigationTrace(id: number | string): Promise<InvestigationTraceResponse> {
  const { data } = await api.get<InvestigationTraceResponse>(`/api/investigations/${id}/trace`)
  return data
}
