import { api } from './client'
import type { RagSearchResult } from '../types'
import { searchRag } from './rag'

export interface KnowledgeDocument {
  id: string
  title: string
  category: string
  source: string
  chunk_count: number
  uploaded_at: string
}

// Semantic search over the knowledge base is served by the RAG pipeline
// (Chroma vector store), so this delegates to /api/rag/search.
export async function searchKnowledgeBase(query: string, top_k = 6): Promise<RagSearchResult> {
  return searchRag(query, top_k)
}

// Document management (list/upload/delete) has no backend route yet - the
// knowledge base is currently populated via scripts/ingest_knowledge_base.py.
// This is prepared for when /api/knowledge ships; callers should treat a
// failure here as "not available yet", not as an error.
export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const { data } = await api.get<KnowledgeDocument[]>('/api/knowledge')
  return data
}

export async function uploadKnowledgeDocument(file: File): Promise<KnowledgeDocument> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<KnowledgeDocument>('/api/knowledge', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
