import { useQuery } from '@tanstack/react-query'
import { getAiStatus } from '../../services/aiStatus'
import { queryKeys } from './queryKeys'

// No dedicated endpoint exists yet - this is prepared for when /api/ai/status
// ships. isError here means "not available", not a real failure.
export function useAiStatusQuery() {
  return useQuery({
    queryKey: queryKeys.aiStatus,
    queryFn: getAiStatus,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
