import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
  searchKnowledgeBase,
  uploadKnowledgeDocument,
} from '../../services/knowledge'
import { queryKeys } from './queryKeys'

export function useKnowledgeSearch() {
  return useMutation({
    mutationFn: ({ query, top_k }: { query: string; top_k?: number }) => searchKnowledgeBase(query, top_k),
  })
}

export function useKnowledgeDocuments() {
  return useQuery({
    queryKey: queryKeys.knowledgeDocuments,
    queryFn: getKnowledgeDocuments,
    refetchOnWindowFocus: false,
  })
}

export function useUploadKnowledgeDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadKnowledgeDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeDocuments })
    },
  })
}

export function useDeleteKnowledgeDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteKnowledgeDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeDocuments })
    },
  })
}
