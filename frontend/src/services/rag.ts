import { api } from './client'
import type { RagSearchResult } from '../types'

export async function searchRag(query: string, top_k = 4): Promise<RagSearchResult> {
  const { data } = await api.post<RagSearchResult>('/api/rag/search', { query, top_k })
  return data
}
