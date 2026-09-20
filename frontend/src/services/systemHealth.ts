import { api } from './client'
import type { HealthCheck } from '../types'

// Conceptually "/api/system/health" - the backend exposes this rollup
// (FastAPI/database/Ollama) under /api/health.
export async function getSystemHealth(): Promise<HealthCheck> {
  const { data } = await api.get<HealthCheck>('/api/health')
  return data
}

// The health check doesn't report the vector DB separately, so we probe the
// RAG service directly - a trivial search that comes back `available: true`
// means Chroma is up and the embedding model responded.
export async function getVectorDbStatus(): Promise<{ available: boolean; message: string | null }> {
  const { data } = await api.post<{ available: boolean; message: string | null }>('/api/rag/search', {
    query: 'status probe',
    top_k: 1,
  })
  return { available: data.available, message: data.message }
}
