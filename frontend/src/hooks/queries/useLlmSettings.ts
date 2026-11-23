import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getLlmSettings, updateLlmSettings } from '../../services/llmSettings'
import { queryKeys } from './queryKeys'

const LLM_SETTINGS_KEY = ['settings', 'llm']

export function useLlmSettingsQuery() {
  return useQuery({
    queryKey: LLM_SETTINGS_KEY,
    queryFn: getLlmSettings,
  })
}

export function useUpdateLlmSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateLlmSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(LLM_SETTINGS_KEY, data)
      queryClient.invalidateQueries({ queryKey: queryKeys.aiStatus })
      queryClient.invalidateQueries({ queryKey: queryKeys.systemHealth })
    },
  })
}
