import { api } from './client'
import type { RagSearchResult } from '../types'
import { searchRag } from './rag'

export interface KnowledgeDocument {
  id: string // relative path inside data/knowledge_base, e.g. "custom/my_runbook.md"
  title: string
  category: string // top-level folder, e.g. response_playbooks, nist, custom
  source: string
  file_type: string // md | txt | pdf | json
  chunk_count: number
  uploaded_at: string | null
  indexed: boolean
  deletable: boolean // only analyst uploads (custom/)
}

export interface KnowledgeUploadResult extends KnowledgeDocument {
  message: string
}

// Semantic search over the knowledge base is served by the RAG pipeline
// (Chroma vector store), so this delegates to /api/rag/search.
export async function searchKnowledgeBase(query: string, top_k = 6): Promise<RagSearchResult> {
  return searchRag(query, top_k)
}

// Lists every document under data/knowledge_base (bundled, downloaded and
// analyst-uploaded) together with how many chunks of it are in the vector store.
export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const { data } = await api.get<KnowledgeDocument[]>('/api/knowledge')
  return data
}

// Saves a .md/.txt/.pdf document to data/knowledge_base/custom/ and indexes it immediately.
export async function uploadKnowledgeDocument(file: File): Promise<KnowledgeUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<KnowledgeUploadResult>('/api/knowledge', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// Removes an analyst-uploaded document (custom/ only) and its indexed chunks.
export async function deleteKnowledgeDocument(id: string): Promise<void> {
  await api.delete(`/api/knowledge/${id.split('/').map(encodeURIComponent).join('/')}`)
}
