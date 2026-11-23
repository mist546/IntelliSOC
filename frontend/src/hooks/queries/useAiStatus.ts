import { useQuery } from '@tanstack/react-query'
import { getAiStatus } from '../../services/aiStatus'
import { queryKeys } from './queryKeys'

export function useAiStatusQuery() {
  return useQuery({
    queryKey: queryKeys.aiStatus,
    queryFn: getAiStatus,
    refetchOnWindowFocus: false,
  })
}
