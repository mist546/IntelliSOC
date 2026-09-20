import { useQuery } from '@tanstack/react-query'
import { getInvestigation } from '../../services/investigations'
import { queryKeys } from './queryKeys'

export function useInvestigationQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.investigation(id ?? ''),
    queryFn: () => getInvestigation(id!),
    enabled: !!id,
  })
}
