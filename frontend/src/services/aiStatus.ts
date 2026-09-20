import { api } from './client'

export interface AiStatus {
  provider: string
  model: string
  embedding_model: string
  reachable: boolean
}

// No dedicated status endpoint exists yet on the backend - this is prepared
// for when /api/ai/status ships. Until then, AI Analysis derives Ollama
// reachability from GET /api/health (checks.ollama) instead of this call.
export async function getAiStatus(): Promise<AiStatus> {
  const { data } = await api.get<AiStatus>('/api/ai/status')
  return data
}
