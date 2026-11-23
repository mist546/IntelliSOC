import { api } from './client'

export interface AiStatus {
  provider: string
  model: string
  embedding_model: string
  reachable: boolean
}

// Reachability reflects the active provider (local daemon or Ollama Cloud).
export async function getAiStatus(): Promise<AiStatus> {
  const { data } = await api.get<AiStatus>('/api/ai/status')
  return data
}
