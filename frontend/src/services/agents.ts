import { api } from './client'
import type { AgentRegisterResponse, CollectorAgent } from '../types'

export async function getAgents(): Promise<CollectorAgent[]> {
  const { data } = await api.get<CollectorAgent[]>('/api/agents')
  return data
}

export async function deleteAgent(id: string): Promise<void> {
  await api.delete(`/api/agents/${id}`)
}

export async function registerAgent(payload: { name: string; hostname: string }): Promise<AgentRegisterResponse> {
  const { data } = await api.post<AgentRegisterResponse>('/api/agents/register', payload)
  return data
}
