import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getLlmSettings, updateLlmSettings } from '../../services/llmSettings'

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
    },
  })
}
