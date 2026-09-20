import { useMutation, useQuery } from '@tanstack/react-query'
import { getKnowledgeDocuments, searchKnowledgeBase } from '../../services/knowledge'
import { queryKeys } from './queryKeys'

export function useKnowledgeSearch() {
  return useMutation({
    mutationFn: ({ query, top_k }: { query: string; top_k?: number }) => searchKnowledgeBase(query, top_k),
  })
}

// The document management API doesn't exist on the backend yet, so this
// query is expected to fail until it does - callers should treat isError as
// "not available", not surface it as an error banner.
export function useKnowledgeDocuments() {
  return useQuery({
    queryKey: queryKeys.knowledgeDocuments,
    queryFn: getKnowledgeDocuments,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
